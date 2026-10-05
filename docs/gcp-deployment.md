# GCP deployment

Nothing in this repository has been deployed to real GCP. The locked Terraform Google provider validates and credential-free mocked plans pass. Live grants, queries, alert filters, SDK normalization and generation still need cloud checks.

Use a dedicated demonstration project for the initial rollout. Terraform defaults to creating a private unprivileged `orders-api` target; set `create_demo_target=false` if monitoring an existing service instead. The service allow-list is deliberately fixed. The API has a single active instance and always-allocated CPU for background work. Monitoring is minute-aligned and may lag; missing data leads to inconclusive recovery, never fabricated health.

The foundation enables APIs and creates Artifact Registry, runtime identities, IAM-authenticated Cloud SQL PostgreSQL with backups/deletion protection, a token secret placeholder, Pub/Sub topics/subscriptions/dead-letter handling, BigQuery analytics/history tables and monitoring. A second phase deploys only immutable image digests into private API/dashboard services and telemetry/analytics jobs, scheduled every minute. BigQuery history uses parameterized MERGE; vectors are versioned 128-dimensional lexical hashes, not Gemini semantic embeddings. Optional index DDL is supplied because Terraform has no dedicated index resource here. Small tables can use brute force.

After explicit user authorization, authenticate locally:

```powershell
gcloud auth login
gcloud auth application-default login
./scripts/gcp/bootstrap.ps1 -ProjectId YOUR_PROJECT_ID -Region us-central1 -Execute
./scripts/gcp/plan.ps1 -ProjectId YOUR_PROJECT_ID -Region us-central1
./scripts/gcp/deploy.ps1 -ProjectId YOUR_PROJECT_ID -Region us-central1 -Execute
./scripts/gcp/verify.ps1 -ProjectId YOUR_PROJECT_ID -Region us-central1 -Execute
```

POSIX equivalents are `sh scripts/gcp/bootstrap.sh --project-id YOUR_PROJECT_ID --region us-central1 --execute`, followed by plan/deploy/verify wrappers with the same flags. Terraform must be installed or present at `.local/terraform/terraform.exe`; gcloud, Docker and bq must be available. The local code/dependencies and frontend build must be verified first.

Commands carry explicit project arguments and preserve global gcloud configuration. Bootstrap creates a deterministically named private versioned GCS state bucket outside the application Terraform stack, initializes its backend, shows a saved plan and applies it only with `-Execute`. Plans containing deletion or replacement are rejected for manual review. Before the first bootstrap, the remote backend bucket does not exist; a plan cannot work until that authorized prerequisite is created. The credential-free verification path always uses `terraform init -backend=false`.

Bootstrap generates a token only if the secret has no enabled version, sends it through stdin, and imports narrowly scoped SQL grants from a private transient SQL file. It does not store the token in Terraform, local files or Git. The API owns its schema objects for Alembic migrations. No database password or downloaded service-account key is required. The bootstrap SQL import and role grants are an explicit live-verification item.

Deploy refuses a dirty checkout, builds Linux amd64 images, pushes commit-tagged artifacts, resolves digests, pins an enabled secret version, plans/applies runtimes, seeds history, creates the optional vector index and verifies endpoints. Generated nonsecret project/digest variables and saved plans stay under ignored `.local/gcp`. Inspect/edit that variable file for advanced options before planning. Foundation bootstrap refuses to run over existing runtimes. Deletion protection is intentional; these scripts contain no automatic destroy path.

Named operators get Cloud Run invocation on the private dashboard/API. The normal browser access path is an authenticated proxy, for example `gcloud run services proxy sentinelops-production-dashboard --project=YOUR_PROJECT_ID --region=us-central1 --port=3000`. Direct private Cloud Run URLs require an appropriate identity token. The server proxy adds API IAM and operator credentials. `verify` performs read-only authenticated checks; its execution switch additionally runs both jobs. The operator token alone is insufficient without Cloud Run IAM invocation.

Optional GitHub deployment uses `enable_github_deployment=true`, the known repository name and immutable GitHub repository ID `1405311636`. WIF is constrained to that ID, branch `codex/build-sentinelops` and `.github/workflows/deploy.yml`. Set the `gcp-production` GitHub environment variables `GCP_PROJECT_ID`, `GCP_REGION`, `GCP_WORKLOAD_IDENTITY_PROVIDER` and `GCP_DEPLOY_SERVICE_ACCOUNT` from Terraform outputs. Configure environment approval protection before production use. No JSON key secret is needed. The manual workflow only updates existing images and jobs; it cannot provision foundations or change IAM. Reconcile its emitted digests into the Terraform variable file before the next infrastructure plan.

Live verification must cover SQL grants/migrations, private invocation and dashboard identity exchange, both scheduled jobs, Pub/Sub persistence-before-ack/redelivery/dead letters, canonical BigQuery analytics, seed/retrieval/index compatibility, Vertex regional/model access, cloud telemetry, approved traffic rollback, actual post-remediation samples/logs and audit. Use an explicitly authorized fault revision only on the demonstration target. Confirm monitoring notifications and billing/cost controls. A successful smoke check is not a completed real incident drill.

References: [Cloud SQL IAM service-account authentication](https://cloud.google.com/blog/topics/developers-practitioners/authenticating-cloud-sql-postgresql-iam-service-accounts), [Cloud SQL SQL import](https://docs.cloud.google.com/sql/docs/postgres/import-export/import-export-sql), [BigQuery vector prefilters](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/search_functions), [Cloud Run IAM permissions](https://docs.cloud.google.com/run/docs/reference/iam/permissions).
