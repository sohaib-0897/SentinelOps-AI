"""Exercise UI failure/loading states using browser fixtures, without changing backend state."""

import argparse
import asyncio
import copy
import json
from pathlib import Path

from playwright.async_api import async_playwright


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dashboard-url", default="http://127.0.0.1:13001")
    parser.add_argument("--axe-script", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    shots = root / "docs/screenshots/redesign"
    report = {"checks": [], "accessibility": [], "page_errors": []}
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            channel="chrome"
            if Path("C:/Program Files/Google/Chrome/Application/chrome.exe").exists()
            else None
        )
        page = await browser.new_page(
            viewport={"width": 1440, "height": 1000}, reduced_motion="reduce"
        )
        page.on("pageerror", lambda e: report["page_errors"].append(str(e)))
        await page.goto(args.dashboard_url + "/overview", wait_until="networkidle")
        records = await (await page.request.get(args.dashboard_url + "/api/v1/incidents")).json()
        assert records, "Run the incident verification before state verification"
        incident = next(i for i in records if i.get("postmortem"))

        async def accessibility(name):
            if not args.axe_script:
                return
            await page.add_script_tag(path=str(args.axe_script))
            result = await page.evaluate(
                """async()=>{const r=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}});return {violations:r.violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))})),passes:r.passes.length}}"""
            )
            report["accessibility"].append({"view": name, **result})
            assert not result["violations"], (name, result)

        await page.goto(
            args.dashboard_url + "/incidents/" + incident["id"], wait_until="networkidle"
        )
        for tab in [
            "Investigation",
            "Evidence",
            "Hypotheses",
            "Timeline",
            "Remediation",
            "Postmortem",
        ]:
            await page.get_by_role("tab", name=tab, exact=False).click()
            if tab == "Evidence":
                await page.locator("details summary").first.click()
                await page.locator("details pre").first.wait_for()
            await accessibility("incident-" + tab)
        await page.get_by_role("tab", name="Investigation", exact=True).focus()
        await page.keyboard.press("ArrowRight")
        assert (
            await page.get_by_role("tab", name="Evidence", exact=False).get_attribute(
                "aria-selected"
            )
            == "true"
        )
        await page.keyboard.press("End")
        assert (
            await page.get_by_role("tab", name="Postmortem", exact=True).get_attribute(
                "aria-selected"
            )
            == "true"
        )
        report["checks"].append("incident_tab_keyboard_navigation")

        async def delayed(route):
            response = await route.fetch()
            await asyncio.sleep(3)
            await route.fulfill(response=response)

        await page.route("**/api/v1/incidents", delayed)
        await page.goto(args.dashboard_url + "/overview", wait_until="domcontentloaded")
        await page.get_by_role("status", name="Loading operational data").wait_for()
        await page.screenshot(path=str(shots / "loading-state.png"))
        await page.get_by_role("status", name="Loading operational data").wait_for(state="hidden")
        await page.unroute("**/api/v1/incidents")
        report["checks"].append("loading_to_real_data")
        fixture = copy.deepcopy(incident)
        fixture["state"] = "AWAITING_APPROVAL"
        fixture["remediation"]["status"] = "proposed"
        fixture["remediation"]["expires_at"] = "2099-01-01T00:00:00Z"

        async def fixture_incident(route):
            await route.fulfill(json=[fixture])

        await page.route("**/api/v1/incidents", fixture_incident)
        # All action endpoints are intercepted so fixture interactions cannot mutate the backend.
        actions = []

        async def reject_action(route):
            actions.append(route.request.url)
            await route.fulfill(
                status=409,
                json={"detail": "Verification fixture: plan expired; review a current plan."},
            )

        await page.route("**/approve-remediation", reject_action)
        await page.route("**/execute-remediation", reject_action)
        await page.goto(
            args.dashboard_url + "/incidents/" + incident["id"], wait_until="networkidle"
        )
        await page.get_by_role("button", name="Review remediation", exact=True).click()
        dialog = page.get_by_role("dialog", name="Review & authorize")
        await dialog.get_by_role("checkbox").check()
        fixture["remediation"]["id"] = "changed-plan-during-review"
        await dialog.get_by_text(
            "The plan changed. Close this drawer and review the new plan.", exact=True
        ).wait_for(timeout=15000)
        assert await dialog.get_by_role("button", name="Approve & execute").is_disabled()
        assert not actions
        await dialog.get_by_role("button", name="Cancel review").click()
        await page.get_by_role("button", name="Review remediation", exact=True).click()
        assert not await dialog.get_by_role("checkbox").is_checked()
        await dialog.get_by_role("checkbox").check()
        await dialog.get_by_role("button", name="Approve & execute").click()
        await dialog.get_by_role("alert").filter(has_text="plan expired").wait_for()
        assert len(actions) == 1 and actions[0].endswith("/approve-remediation")
        await accessibility("approval-error")
        await page.screenshot(path=str(shots / "approval-error-state.png"))
        await dialog.get_by_role("button", name="Cancel review").click()
        await page.unroute("**/api/v1/incidents")
        await page.unroute("**/approve-remediation")
        await page.unroute("**/execute-remediation")
        report["checks"].extend(
            [
                "changed_plan_disables_execution",
                "review_resets_acknowledgement",
                "approval_failure_keeps_drawer_open",
                "approval_failure_never_executes",
            ]
        )
        await page.goto(args.dashboard_url + "/overview", wait_until="networkidle")
        await page.keyboard.press("Control+k")
        dialog = page.get_by_role("dialog", name="Jump to workspace")
        assert await page.get_by_role("textbox", name="Find a page").evaluate(
            "(e)=>e===document.activeElement"
        )
        await page.get_by_role("textbox", name="Find a page").fill("not-a-page")
        await dialog.get_by_text("No pages match", exact=False).wait_for()
        await accessibility("command-empty")
        await page.keyboard.press("Escape")
        assert not await dialog.is_visible()
        await page.goto(args.dashboard_url + "/does-not-exist", wait_until="networkidle")
        assert (await page.reload()).status == 404
        report["checks"].extend(["command_search_focus_and_empty_state", "unknown_route_404"])
        assert not report["page_errors"], report["page_errors"]
        await browser.close()
    (root / "docs/verification/redesign-state-checks.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
