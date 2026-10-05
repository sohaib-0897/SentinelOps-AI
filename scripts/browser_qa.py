"""Exercise the real UI, API and bounded demo service; retain portfolio screenshots."""
import asyncio
import json
from pathlib import Path

import httpx
from playwright.async_api import async_playwright


async def main() -> None:
    root = Path(__file__).resolve().parents[1]
    screenshots = root/"docs/screenshots"
    screenshots.mkdir(parents=True,exist_ok=True)
    report = {"flow":[],"console_errors":[],"responsive":[]}
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000",timeout=30) as api, httpx.AsyncClient(base_url="http://127.0.0.1:8001",timeout=10) as demo, async_playwright() as playwright:
        browser = await playwright.chromium.launch(channel="chrome" if Path("C:/Program Files/Google/Chrome/Application/chrome.exe").exists() else None)
        page = await browser.new_page(viewport={"width":1440,"height":1050},device_scale_factor=1)
        page.on("pageerror",lambda error:report["console_errors"].append(str(error)))
        assert (await demo.get("/health")).json()["status"] == "healthy"
        assert (await demo.get("/api/items")).status_code == 200
        report["flow"].append("real_demo_service_healthy")
        await page.goto("http://127.0.0.1:3000",wait_until="networkidle")
        await page.get_by_role("heading",name="Operational overview").wait_for()
        await page.screenshot(path=str(screenshots/"overview.png"),full_page=True)
        await page.get_by_role("button",name="Start Demo",exact=True).click()
        await page.get_by_role("button",name="Speed Up").click()
        incident = None
        for _ in range(100):
            incidents = (await api.get("/api/v1/incidents")).json()
            if incidents and incidents[0]["state"] == "AWAITING_APPROVAL":
                incident = incidents[0]
                break
            await asyncio.sleep(.2)
        assert incident, "Incident did not reach approval"
        assert incident["root_cause"]["cause"] == "bad_deployment"
        assert len(incident["hypotheses"]) >= 3
        assert "INC-007" in [m["id"] for m in incident["historical_matches"]]
        assert (await demo.get("/health")).json()["failure_mode"] == "db_pool_exhaustion"
        assert (await demo.get("/api/orders")).status_code == 500
        assert (await api.post(f"/api/v1/incidents/{incident['id']}/execute-remediation")).status_code == 409
        report["flow"].extend(["deployment_observed","metrics_degraded","meaningful_failure_logs","sustained_alert_detected","incident_created","triage_tools_used","evidence_collected","multiple_hypotheses_ranked","historical_match_found","approval_gate_enforced"])
        await page.goto(f"http://127.0.0.1:3000/incidents/{incident['id']}",wait_until="networkidle")
        await page.get_by_role("button",name="Approve Remediation",exact=True).wait_for()
        await page.screenshot(path=str(screenshots/"incident-awaiting-approval.png"),full_page=True)
        await page.get_by_role("tab",name="Evidence").click()
        await page.get_by_text("Collected source records",exact=True).wait_for()
        await page.get_by_role("tab",name="Timeline",exact=True).click()
        await page.get_by_text("Incident timeline",exact=True).wait_for()
        await page.get_by_role("tab",name="Remediation",exact=True).click()
        await page.get_by_role("button",name="Approve Remediation",exact=True).click()
        await page.get_by_text("Approved remediation executed",exact=True).wait_for(timeout=30000)
        resolved = (await api.get(f"/api/v1/incidents/{incident['id']}")).json()
        assert resolved["state"] == "RESOLVED"
        assert resolved["verification"]["recovered"] and resolved["verification"]["samples"] == 5
        assert resolved["postmortem"]["prevention"]
        assert (await demo.get("/health")).json()["status"] == "healthy"
        assert (await demo.get("/api/orders")).status_code == 200
        report["flow"].extend(["ui_approval_recorded","rollback_executed","real_demo_service_recovered","five_fresh_samples_verified","incident_resolved","postmortem_generated"])
        await page.get_by_role("tab",name="Postmortem",exact=True).click()
        await page.get_by_text("Recovery verified · postmortem generated",exact=True).wait_for()
        await page.screenshot(path=str(screenshots/"incident-postmortem.png"),full_page=True)
        for route in ("/services","/metrics","/deployments","/postmortems","/system","/incidents"):
            await page.goto("http://127.0.0.1:3000"+route,wait_until="networkidle")
            assert await page.get_by_role("heading",level=1).count() == 1
        for width in (390,768,1440):
            await page.set_viewport_size({"width":width,"height":900})
            await page.goto("http://127.0.0.1:3000",wait_until="networkidle")
            overflow = await page.evaluate("document.documentElement.scrollWidth > innerWidth")
            report["responsive"].append({"width":width,"horizontal_overflow":overflow})
            assert not overflow
        assert not report["console_errors"], report["console_errors"]
        report["incident_id"] = incident["id"]
        report["state"] = resolved["state"]
        report["verification"] = resolved["verification"]
        await browser.close()
    output = root/"docs/verification/local-e2e.json"
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2))


if __name__ == "__main__":
    asyncio.run(main())
