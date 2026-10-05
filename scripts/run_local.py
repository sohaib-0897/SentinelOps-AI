"""Run API, real demo service and dashboard with coordinated shutdown."""
import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def wait_ready(url: str, processes: list[subprocess.Popen], seconds: int = 120) -> None:
    deadline = time.monotonic()+seconds
    while time.monotonic() < deadline:
        if any(process.poll() is not None for process in processes):
            raise RuntimeError("A service exited; inspect .local service logs")
        try:
            with urllib.request.urlopen(url, timeout=2) as response:  # noqa: S310 -- fixed loopback HTTP endpoints
                if response.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError):
            time.sleep(.5)
    raise RuntimeError(f"Service readiness timed out: {url}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--production", action="store_true", help="Use the built Next application")
    arguments = parser.parse_args()
    os.chdir(ROOT)
    local = ROOT/".local"
    local.mkdir(exist_ok=True)
    commands = [
        [sys.executable,"-m","uvicorn","sentinelops.demo_service:app","--host","127.0.0.1","--port","8001"],
        [sys.executable,"-m","uvicorn","sentinelops.api:app","--host","127.0.0.1","--port","8000"],
        [shutil.which("node") or "node",str(ROOT/"apps/dashboard/node_modules/next/dist/bin/next"),"start" if arguments.production else "dev","--hostname","127.0.0.1","--port","3000"],
    ]
    environment = {**os.environ,"CONNECT_DEMO_SERVICE":"true","DEMO_SERVICE_URL":"http://127.0.0.1:8001"}
    processes = []
    handles = []
    def stop(signum=None, frame=None):
        for process in reversed(processes):
            if process.poll() is None:
                process.terminate()
    signal.signal(signal.SIGINT,stop)
    signal.signal(signal.SIGTERM,stop)
    try:
        for name, command in zip(("demo-service","incident-api","dashboard"),commands,strict=True):
            handle = (local/f"{name}.log").open("w",encoding="utf-8")
            handles.append(handle)
            processes.append(subprocess.Popen(command,cwd=ROOT/"apps/dashboard" if name == "dashboard" else ROOT,env=environment,stdout=handle,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0))  # noqa: S603 -- fixed local service commands; no shell
        for url in ("http://127.0.0.1:8001/health","http://127.0.0.1:8000/health","http://127.0.0.1:3000"):
            wait_ready(url,processes)
        print("SentinelOps AI ready: http://127.0.0.1:3000 | API docs: http://127.0.0.1:8000/docs",flush=True)
        if arguments.demo:
            request = urllib.request.Request("http://127.0.0.1:8000/api/v1/demo/start",data=json.dumps({"scenario":"bad-deployment"}).encode(),headers={"Content-Type":"application/json"},method="POST")
            try:
                with urllib.request.urlopen(request,timeout=10):  # noqa: S310 -- fixed loopback mutation
                    print("Bad-deployment demo started; approve remediation in the dashboard.",flush=True)
            except urllib.error.HTTPError as error:
                if error.code == 409:
                    print("An existing incident is retained. Use the dashboard to approve it or Restart.",flush=True)
                else:
                    raise
        while all(process.poll() is None for process in processes):
            time.sleep(.5)
    finally:
        stop()
        for process in processes:
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        for handle in handles:
            handle.close()


if __name__ == "__main__":
    main()
