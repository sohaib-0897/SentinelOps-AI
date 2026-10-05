# Final GCP setup

Request these only after the local completion checkpoint, clean pushed branch and review PR:

1. GCP project ID, preferably a dedicated demonstration project.
2. Preferred region; `us-central1` is the default.
3. Confirmation billing is enabled.
4. Local gcloud login and Application Default Credentials authentication.
5. Explicit permission to create the state bucket, run the reviewed Terraform apply and deploy the images.

Do not request API keys, passwords or service-account JSON. The user account needs sufficient project/API/IAM/storage/SQL/Run permissions for initial provisioning. Once project/region and authorization are known, automate the state bucket, APIs, identities, secret generation, SQL grants, builds, image publication, Terraform phases, history seed/index, endpoint verification and jobs. Review any destructive/replacement plan separately; the scripts refuse it.

No real project is recorded in the example variables. No cloud resources or secrets have been created by the local implementation session. Cloud-capable SDKs and ADK have been installed/tested with mocks or construction only.

The minimum initial commands are described in `gcp-deployment.md`. Separate server operator and ingestion tokens are generated directly into Secret Manager during authorized bootstrap. All runtime access uses ADC, service identities, scoped impersonation or optional GitHub federation. Optional notification channels and GitHub environment variables can be configured after the first live deployment; they are not prerequisites for local completion.

Still unverified: Google resource/API acceptance, Cloud SQL role grants and PostgreSQL backfills, Cloud Run identity tokens and IAM conditions, scheduler invocation, SDK data shapes, Monitoring availability/lag and alert delivery, Pub/Sub ordering/redelivery/dead letters, BigQuery MERGE/canonical views/vector index, Vertex model access and ADK responses, cloud traffic rollback and fresh-sample recovery. Keep README/cloud status honest until each live check actually passes.

The infrastructure checkpoint means code, scripts and credential-free checks are complete. The local completion checkpoint additionally requires fresh backend/frontend/evaluation/container/browser checks and retained evidence. Neither checkpoint claims real GCP deployment.
