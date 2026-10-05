"""Shared Windows/POSIX deployment tooling. No cloud mutations without --execute."""
import argparse
import asyncio
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
INFRA = ROOT / "infra/terraform"


def executable(name: str) -> str:
    found = shutil.which(name)
    if not found and name == "terraform":
        candidate = ROOT / ".local/terraform/terraform.exe"
        found = str(candidate) if candidate.exists() else None
    if not found:
        raise RuntimeError(f"Install {name} before this operation")
    return found


def run(name: str, *args: str, capture: bool = False, data: bytes | None = None) -> str:
    result = subprocess.run(  # noqa: S603 -- resolved executable, fixed argument arrays; no shell
        [executable(name), *args], cwd=ROOT, input=data, check=True,
        stdout=subprocess.PIPE if capture else None,
    )
    return result.stdout.decode().strip() if capture else ""


class Deployment:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        if not re.fullmatch(r"[a-z][a-z0-9-]{4,28}[a-z0-9]", args.project_id):
            raise ValueError("Invalid GCP project ID")
        if not re.fullmatch(r"[a-z]+-[a-z]+[0-9]", args.region):
            raise ValueError("Invalid region")
        self.local = ROOT / ".local/gcp"
        self.local.mkdir(parents=True, exist_ok=True)
        self.var_file = self.local / f"{args.project_id}-{args.environment}.tfvars.json"
        self.plan_file = self.local / f"{args.project_id}-{args.environment}.tfplan"
        self.values: dict[str, Any] = json.loads(self.var_file.read_text()) if self.var_file.exists() else {}
        self.values.update(project_id=args.project_id, region=args.region, environment=args.environment)

    def gcloud(self, *args: str, capture: bool = False, data: bytes | None = None) -> str:
        return run("gcloud", *args, f"--project={self.args.project_id}", capture=capture, data=data)

    def tf(self, *args: str, capture: bool = False) -> str:
        return run("terraform", f"-chdir={INFRA}", *args, capture=capture)

    def preflight(self) -> None:
        self.gcloud("version", capture=True)
        accounts = json.loads(self.gcloud("auth", "list", "--filter=status:ACTIVE", "--format=json", capture=True))
        if not accounts:
            raise RuntimeError("Run gcloud auth login and gcloud auth application-default login first")
        self.gcloud("auth", "application-default", "print-access-token", capture=True)
        billing = json.loads(self.gcloud("billing", "projects", "describe", self.args.project_id, "--format=json", capture=True))
        if not billing.get("billingEnabled"):
            raise RuntimeError("Billing must be enabled")
        self.tf("init", "-input=false")
        self.tf("validate")
        # Every command carries --project; the user's global gcloud project is untouched.
        if "dashboard_invokers" not in self.values:
            account = accounts[0]["account"]
            if not re.fullmatch(r"[A-Za-z0-9._%+@-]+", account):
                raise ValueError("Invalid active account")
            member = ("serviceAccount:" if account.endswith(".gserviceaccount.com") else "user:") + account
            self.values["dashboard_invokers"] = [member]

    def output(self) -> dict[str, Any]:
        return {key: item["value"] for key, item in json.loads(self.tf("output", "-json", capture=True)).items()}

    def plan(self) -> None:
        self.var_file.write_text(json.dumps(self.values, indent=2) + "\n")
        self.tf("plan", "-input=false", f"-var-file={self.var_file}", f"-out={self.plan_file}")
        print(f"Review the saved plan: {self.plan_file}")

    def apply(self) -> None:
        if not self.args.execute:
            raise RuntimeError("Cloud mutation requires --execute after user authorization")
        self.plan()
        change = json.loads(self.tf("show", "-json", str(self.plan_file), capture=True))
        if any("delete" in resource["change"]["actions"] for resource in change.get("resource_changes", [])):
            raise RuntimeError("Plan includes deletion/replacement; review and apply it manually with explicit confirmation")
        self.tf("apply", "-input=false", str(self.plan_file))

    def bootstrap(self) -> None:
        if not self.args.execute:
            self.values.setdefault("deploy_runtimes", False)
            self.plan()
            return
        existing = self.output()
        if existing.get("api_url"):
            raise RuntimeError("Runtimes already exist; use deploy to preserve them")
        self.values["deploy_runtimes"] = False
        self.apply()
        outputs = self.output()
        secret_id = outputs["operator_secret"]
        versions = json.loads(self.gcloud("secrets", "versions", "list", secret_id, "--filter=state:ENABLED", "--format=json", capture=True))
        if not versions:
            self.gcloud("secrets", "versions", "add", secret_id, "--data-file=-", data=secrets.token_hex(32).encode())
        # No token value is written to disk, logs, arguments, Terraform or Git.
        user = outputs["cloud_sql_user"]
        if not re.fullmatch(r"[a-z0-9@.-]+", user):
            raise ValueError("Invalid SQL IAM user")
        sql = f'GRANT CONNECT ON DATABASE sentinelops TO "{user}";\nGRANT USAGE, CREATE ON SCHEMA public TO "{user}";\n'
        grant_file = self.local / "database-grants.sql"
        grant_file.write_text(sql)
        destination = f"gs://{outputs['bootstrap_bucket']}/database-grants.sql"
        self.gcloud("storage", "cp", str(grant_file), destination)
        self.gcloud("sql", "import", "sql", outputs["sql_instance_name"], destination, "--database=sentinelops", "--quiet")
        self.gcloud("storage", "rm", destination)
        print("Foundation, secret placeholder/version and IAM database grants are ready")

    def deploy(self) -> None:
        if not self.args.execute:
            print("Deployment requires --execute; run bootstrap and plan first")
            return
        outputs = self.output()
        if not outputs.get("image_repository"):
            raise RuntimeError("Run bootstrap --execute first")
        repository = outputs["image_repository"]
        host = repository.split("/", 1)[0]
        self.gcloud("auth", "configure-docker", host, "--quiet")
        sha = run("git", "rev-parse", "HEAD", capture=True)
        if run("git", "status", "--porcelain", capture=True):
            raise RuntimeError("Deploy only a clean committed checkout")
        for name, context in [("api", "."), ("dashboard", "apps/dashboard")]:
            image = f"{repository}/{name}:{sha}"
            run("docker", "build", "--platform=linux/amd64", "-t", image, context)
            run("docker", "push", image)
            digest = self.gcloud("artifacts", "docker", "images", "describe", image, "--format=value(image_summary.digest)", capture=True)
            if not re.fullmatch(r"sha256:[a-f0-9]{64}", digest):
                raise ValueError("Registry did not return an immutable digest")
            self.values[f"{name}_image"] = f"{repository}/{name}@{digest}"
        versions = json.loads(self.gcloud("secrets", "versions", "list", outputs["operator_secret"], "--filter=state:ENABLED", "--format=json", capture=True))
        if not versions:
            raise RuntimeError("Bootstrap the operator secret before runtime deployment")
        self.values["operator_secret_version"] = str(max(int(v["name"].rsplit("/", 1)[-1]) for v in versions))
        self.values["deploy_runtimes"] = True
        self.apply()
        outputs = self.output()
        environment = {**os.environ, "GCP_PROJECT_ID": self.args.project_id, "BIGQUERY_DATASET": outputs["bigquery_dataset"]}
        subprocess.run([sys.executable, "-m", "scripts.seed_cloud_history"], cwd=ROOT, env=environment, check=True)  # noqa: S603 -- fixed module and interpreter
        sql = (INFRA / "vector-index.sql").read_text().replace("PROJECT_ID", self.args.project_id).replace("DATASET", outputs["bigquery_dataset"])
        run("bq", "query", f"--project_id={self.args.project_id}", f"--location={self.args.region}", "--use_legacy_sql=false", sql)
        self.verify()

    def verify(self) -> None:
        outputs = self.output()
        api_url, dashboard_url = outputs.get("api_url"), outputs.get("dashboard_url")
        if not api_url or not dashboard_url:
            raise RuntimeError("Deploy runtimes before verifying them")
        for url in [api_url, dashboard_url]:
            if not re.fullmatch(r"https://[a-z0-9.-]+\.run\.app", url):
                raise ValueError("Refuse unexpected endpoint URL")
        token = self.gcloud("auth", "print-identity-token", capture=True)
        from sentinelops.providers.gcp.secrets import GCPSecretManager
        operator = asyncio.run(GCPSecretManager(self.args.project_id).access(outputs["operator_secret"], self.values.get("operator_secret_version", "1")))
        def get(url: str, headers: dict[str, str]) -> Any:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as response:  # noqa: S310 -- validated Cloud Run https origin
                return response.read()
        headers = {"Authorization": f"Bearer {operator}", "X-Serverless-Authorization": f"Bearer {token}"}
        status = json.loads(get(api_url + "/api/v1/system/status", headers))
        assert status["mode"] == "production" and not status["demo_mode"]
        for route in ["/api/v1/incidents", "/api/v1/services", "/api/v1/deployments"]:
            get(api_url + route, headers)
        get(dashboard_url, {"Authorization": f"Bearer {token}"})
        if self.args.execute:
            for job in outputs["worker_jobs"].values():
                self.gcloud("run", "jobs", "execute", job, f"--region={self.args.region}", "--wait")
        print("Authenticated endpoint checks passed; --execute also runs both jobs. Test live incident/approval flow separately")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["bootstrap", "plan", "deploy", "verify"])
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--region", default="us-central1")
    parser.add_argument("--environment", choices=["production", "staging"], default="production")
    parser.add_argument("--execute", action="store_true", help="Explicit authorization for cloud mutations")
    args = parser.parse_args()
    deployment = Deployment(args)
    deployment.preflight()
    getattr(deployment, args.command)()


if __name__ == "__main__":
    main()
