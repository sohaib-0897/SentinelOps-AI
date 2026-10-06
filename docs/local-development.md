# Local development

Run from the repository directory, not its parent. Python 3.12, Node 22, uv 0.9.21 and Docker Desktop are the verified tool families. Lock files are authoritative. `.npmrc` preserves the established reproducible peer-resolution mode. Never commit `.env`, credentials, Terraform state or `.local` artifacts.

```powershell
uv sync --frozen --extra gcp
Set-Location apps/dashboard
npm ci
npm audit
npm run lint
npm run typecheck
npm test
npm run build
Set-Location ../..
uv run --extra gcp pytest -q
uv run --extra gcp ruff check sentinelops tests scripts
uv run --extra gcp mypy sentinelops
uv run python -m sentinelops.evaluation.run
```

Cloud dependencies install without contacting GCP. Local/test providers never require ADC. Copy `.env.example` to `.env` only if changing settings. Keep `APP_ENV=local` and `DEMO_MODE=true` for the demo. The native launcher supports `--production` for the already-built dashboard and `--demo` to start the scenario immediately. Its logs are under `.local`.

```powershell
docker compose config --quiet
docker compose build
docker compose up -d --wait
uv run python scripts/browser_qa.py
```

If another application owns the default ports, preserve it:

```powershell
$env:API_PORT='18000'
$env:DEMO_PORT='18001'
$env:DASHBOARD_PORT='13000'
docker compose up -d --wait
uv run python scripts/browser_qa.py --api-url http://127.0.0.1:18000 --demo-url http://127.0.0.1:18001 --dashboard-url http://127.0.0.1:13000
```

Use the same port environment when operating Compose. `docker compose down` stops only this project and retains its incident volume. Avoid `down -v` unless deliberately discarding that project's history. No global Docker prune is required. For an internal missing-blob error, retry individual builds and inspect the selected builder before considering narrowly scoped cache repair.

Browser QA uses installed Chrome on Windows or Playwright Chromium elsewhere. Install Chromium with `uv run playwright install chromium` if needed. Start with a healthy demo service and no unfinished incident, or review/restart the retained scenario through the UI. The script regenerates screenshots and its JSON report.

Terraform checks need no cloud authentication:

```powershell
.local/terraform/terraform.exe -chdir=infra/terraform fmt -check -recursive
.local/terraform/terraform.exe -chdir=infra/terraform init -backend=false
.local/terraform/terraform.exe -chdir=infra/terraform validate
.local/terraform/terraform.exe -chdir=infra/terraform test
```

Use `terraform` directly if installed. Native Terraform tests mock the provider and plan both foundation and runtime configurations. CI performs fresh dependency installs, all these checks, Docker builds and real browser QA on Linux.

The root URL is the product landing page. The operational dashboard is at `/overview`. See [the interface guide](UI_REDESIGN.md) and run `python scripts/redesign_qa.py` with your port arguments for the expanded route, drawer, responsive, and state verification.
