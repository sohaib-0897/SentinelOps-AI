"""Verify the redesigned workspace against the real local API and demo service."""

import argparse
import asyncio
import json
from pathlib import Path

import httpx
from playwright.async_api import async_playwright


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dashboard-url", default="http://127.0.0.1:13001")
    parser.add_argument("--api-url", default="http://127.0.0.1:18000")
    parser.add_argument("--demo-url", default="http://127.0.0.1:18001")
    parser.add_argument(
        "--axe-script", type=Path, help="Optional local axe-core axe.min.js for WCAG checks"
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    shots = root / "docs/screenshots/redesign"
    shots.mkdir(parents=True, exist_ok=True)
    report = {"checks": [], "page_errors": [], "responsive": [], "accessibility": []}
    async with (
        httpx.AsyncClient(base_url=args.api_url, timeout=40, trust_env=False) as api,
        httpx.AsyncClient(base_url=args.demo_url, timeout=30, trust_env=False) as demo,
        async_playwright() as p,
    ):
        browser = await p.chromium.launch(
            channel="chrome"
            if Path("C:/Program Files/Google/Chrome/Application/chrome.exe").exists()
            else None
        )
        page = await browser.new_page(
            viewport={"width": 1440, "height": 1000}, reduced_motion="reduce"
        )
        page.set_default_timeout(30000)
        page.on("pageerror", lambda e: report["page_errors"].append(str(e)))

        async def goto(route):
            response = await page.goto(
                args.dashboard_url + route, wait_until="domcontentloaded", timeout=120000
            )
            assert response and response.status == 200, (
                route,
                response.status if response else None,
            )
            await page.wait_for_load_state("networkidle")

        async def shot(name):
            await page.screenshot(
                path=str(shots / (name + ".png")), full_page=name != "approval-review"
            )
            print("Captured", name, flush=True)

        async def accessibility(label):
            if not args.axe_script:
                return
            await page.add_script_tag(path=str(args.axe_script))
            result = await page.evaluate(
                """async()=>{const r=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}});return {violations:r.violations.map(v=>({id:v.id,impact:v.impact,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))})),passes:r.passes.length}}"""
            )
            report["accessibility"].append({"view": label, **result})
            assert not result["violations"], (label, result["violations"])

        await goto("/")
        assert await page.locator("h1").count() == 1
        await page.get_by_role("tab", name="Approve", exact=False).click()
        await page.get_by_role("heading", name="Your infrastructure. Your decision.").wait_for()
        await page.get_by_role("tab", name="Detect", exact=False).click()
        await shot("landing")
        await page.get_by_role("link", name="Enter mission control").click()
        await page.get_by_role("heading", name="Operational overview").wait_for()
        await page.get_by_role("button", name="Jump to a page").click()
        await page.get_by_role("textbox", name="Find a page").fill("metrics")
        await page.get_by_role("dialog").get_by_role("link", name="Metrics", exact=True).click()
        await page.get_by_role("heading", name="Metrics", exact=True).wait_for()
        await page.get_by_role("button", name="Last 10", exact=True).click()
        assert (
            await page.get_by_role("button", name="Last 10").get_attribute("aria-pressed") == "true"
        )
        report["checks"].extend(
            ["landing_workflow_tabs", "command_navigation", "metric_sample_window"]
        )
        await goto("/overview")
        await page.get_by_role("button", name="Restart demo", exact=True).click()
        await page.get_by_role("button", name="Pause", exact=True).click()
        await page.get_by_role("button", name="Resume", exact=True).click()
        speed = page.get_by_role("button", name="Speed Up", exact=True)
        if await speed.count():
            await speed.click()
        incident = None
        for _ in range(150):
            incidents = (await api.get("/api/v1/incidents")).json()
            if incidents and incidents[0]["state"] == "AWAITING_APPROVAL":
                incident = incidents[0]
                break
            await asyncio.sleep(0.3)
        assert incident, "Incident did not reach approval"
        assert incident["root_cause"]["cause"] == "bad_deployment"
        assert len(incident["hypotheses"]) >= 3
        assert incident["historical_matches"]
        assert (
            await api.post(f"/api/v1/incidents/{incident['id']}/execute-remediation")
        ).status_code == 409
        assert (await demo.get("/api/orders")).status_code == 500
        report["checks"].extend(
            [
                "simulator_restart_pause_resume_speed",
                "live_degradation",
                "evidence_hypotheses_history",
                "execution_blocked_before_approval",
            ]
        )
        await page.get_by_role("link", name="Open incident", exact=True).wait_for()
        await shot("overview-active")
        await goto("/incidents")
        await page.get_by_role("button", name="Needs approval", exact=True).click()
        assert await page.locator("tbody tr").count() >= 1
        await page.get_by_role("textbox", name="Search incidents").fill("does-not-exist")
        await page.get_by_role("heading", name="No matching incidents").wait_for()
        await page.get_by_role("textbox", name="Search incidents").fill("")
        await shot("incidents")
        await goto("/incidents/" + incident["id"])
        await page.get_by_role("button", name="Review remediation", exact=True).wait_for()
        await shot("incident-command")
        for tab in [
            "Evidence",
            "Hypotheses",
            "Timeline",
            "Remediation",
            "Postmortem",
            "Investigation",
        ]:
            await page.get_by_role("tab", name=tab, exact=False).click()
            assert await page.get_by_role("tabpanel").is_visible()
        await page.get_by_role("button", name="Review remediation", exact=True).click()
        dialog = page.get_by_role("dialog", name="Review & authorize")
        await dialog.wait_for()
        approve = dialog.get_by_role("button", name="Approve & execute", exact=True)
        assert await approve.is_disabled()
        await page.keyboard.press("Escape")
        assert not await dialog.is_visible()
        await page.get_by_role("button", name="Review remediation", exact=True).click()
        assert not await dialog.get_by_role("checkbox").is_checked()
        await dialog.get_by_role("checkbox").check()
        await shot("approval-review")
        await accessibility("approval-review")
        # Native modal contains keyboard focus and exposes the exact plan.
        assert await dialog.locator("text=" + incident["remediation"]["id"]).count() == 1
        for _ in range(8):
            await page.keyboard.press("Tab")
            assert await page.evaluate(
                'document.querySelector("dialog[open]").contains(document.activeElement)'
            )
        await approve.click()
        await page.get_by_text("Approved remediation executed", exact=True).wait_for(timeout=60000)
        resolved = (await api.get("/api/v1/incidents/" + incident["id"])).json()
        assert resolved["state"] == "RESOLVED"
        assert resolved["verification"]["recovered"] and resolved["verification"]["samples"] == 5
        assert (await demo.get("/api/orders")).status_code == 200
        report["checks"].extend(
            [
                "incident_tabs",
                "drawer_cancel_focus_and_confirmation",
                "exact_plan_approval",
                "real_rollback",
                "five_fresh_recovery_samples",
                "real_service_recovered",
            ]
        )
        await page.get_by_role("tab", name="Postmortem", exact=True).click()
        await page.get_by_text("Recovery verified · postmortem generated", exact=True).wait_for()
        async with page.expect_download() as download:
            await page.get_by_role("button", name="Export JSON").click()
        assert (await download.value).suggested_filename == f"postmortem-{incident['id']}.json"
        await shot("postmortem")
        await goto("/postmortems")
        await page.locator(".postmortem-card").first.click()
        assert (
            await page.get_by_role("tab", name="Postmortem", exact=True).get_attribute(
                "aria-selected"
            )
            == "true"
        )
        report["checks"].extend(["postmortem_export", "postmortem_direct_link"])
        routes = [
            "/",
            "/overview",
            "/incidents",
            "/incidents/" + incident["id"],
            "/services",
            "/metrics",
            "/deployments",
            "/postmortems",
            "/system",
        ]
        for width in [390, 768, 1440]:
            await page.set_viewport_size({"width": width, "height": 1000})
            for route in routes:
                await goto(route)
                assert await page.locator("h1").count() == 1, route
                overflow = await page.evaluate("document.documentElement.scrollWidth > innerWidth")
                report["responsive"].append(
                    {"width": width, "route": route, "horizontal_overflow": overflow}
                )
                assert not overflow, (width, route)
                if width == 1440:
                    await accessibility(route)
                if width == 1440 or (
                    width == 390 and route in ["/", "/overview", "/incidents/" + incident["id"]]
                ):
                    await shot(
                        (
                            "incident-resolved"
                            if route.startswith("/incidents/")
                            else (route.strip("/") or "landing")
                        )
                        + f"-{width}"
                    )
        await page.keyboard.press("Control+k")
        await page.get_by_role("dialog", name="Jump to workspace").wait_for()
        await page.keyboard.press("Escape")
        report["checks"].append("all_routes_responsive_and_command_shortcut")
        (root / "docs/verification/redesign-e2e.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8"
        )
        await goto("/incidents/not-an-incident")
        await page.get_by_role("heading", name="Incident unavailable", level=1).wait_for()
        report["checks"].append("missing_incident_state")
        # Isolated browser fixtures verify unavailable and empty UI states without mutating data.
        await page.route("**/api/v1/incidents", lambda route: route.fulfill(json=[]))
        await goto("/incidents")
        await page.get_by_role("heading", name="No incidents to investigate").wait_for()
        await shot("empty-state")
        await page.unroute("**/api/v1/incidents")
        await page.route(
            "**/api/v1/**",
            lambda route: route.fulfill(
                status=503, json={"detail": "Verification: provider unavailable"}
            ),
        )
        await goto("/overview")
        await page.locator('.error-banner[role="alert"]').wait_for()
        await shot("error-state")
        await page.unroute("**/api/v1/**")
        await page.get_by_role("button", name="Retry connection").click()
        await page.locator('.error-banner[role="alert"]').wait_for(state="hidden")
        report["checks"].extend(["empty_state_fixture", "error_state_fixture", "retry_reconnect"])
        timeline = (await api.get(f"/api/v1/incidents/{incident['id']}/timeline")).json()
        assert [e["timestamp"] for e in timeline] == sorted(e["timestamp"] for e in timeline)
        audit = (await api.get("/api/v1/audit")).json()
        operations = {e["operation"] for e in audit if e["incident_id"] == incident["id"]}
        assert {
            "remediation_approved",
            "execution_claimed",
            "remediation_executed",
            "recovery_verified",
        } <= operations
        reconnect = await page.evaluate(
            """async()=>{const connect=()=>new Promise((resolve,reject)=>{const source=new EventSource('/api/v1/events');const timeout=setTimeout(()=>{source.close();reject('timeout')},10000);source.addEventListener('connected',e=>{clearTimeout(timeout);source.close();resolve(JSON.parse(e.data))})});return [await connect(),await connect()]}"""
        )
        assert all(e["type"] == "resync" for e in reconnect)
        report["checks"].extend(
            ["chronological_timeline", "durable_execution_audit", "two_sse_proxy_reconnections"]
        )
        assert not report["page_errors"], report["page_errors"]
        report["incident_id"] = incident["id"]
        report["verification"] = resolved["verification"]
        await browser.close()
    (root / "docs/verification/redesign-e2e.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
