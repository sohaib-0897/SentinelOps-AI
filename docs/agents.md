# Agent architecture

| Agent | Responsibility |
|---|---|
| Triage | Classify service, observed symptoms and severity through typed read tools |
| Investigator | Collect timestamped logs, metrics, revisions and configuration evidence |
| Historical | Retrieve matches and retain provenance |
| Root cause | Rank corroborated signatures; abstain when independent evidence is absent |
| Remediation | Produce a bounded risk-classified plan from supported rules/runbooks |
| Verification | Require five fresh post-action observations, health, target revision and log checks |
| Postmortem | Produce factual impact/response/follow-up records after verified resolution |

Typed `AgentTools` validate identifiers and bounds. Runbooks come from a fixed filename mapping. LLM providers have only `explain`; they do not get tools for execution, approval, IAM or arbitrary shell commands.

`LLM_PROVIDER=deterministic` is the local/test default. `vertex` uses schema-constrained Gemini generation. `adk` uses a Vertex-configured ADK LlmAgent and Runner with no tools, sub-agents or code executor. It sends at most thirty redacted evidence summaries, limits generation to one model call, sixteen events and forty-five seconds, validates the final explanation schema, and deletes its ephemeral session. No process-global API-key or Vertex environment mutation is used to configure the model client.

The domain rules select the cause, evidence IDs and remediation before approval. Model prose cannot alter those fields. Invalid generation fails investigation safely; unknown evidence does not become a confident diagnosis. Heuristic scores are not model probabilities. ADK integration is mock-tested plus SDK-constructed without network generation; actual Vertex output remains unverified.

In cloud mode, recovery polling accommodates minute-aligned Monitoring data. Missing observations or required metrics never count as recovery. Only Cloud Run traffic revision changes are supported by the cloud executor; restart/capacity actions remain local demonstrations.

References: [Google ADK agent/output-schema guidance](https://github.com/google/adk-docs/blob/main/docs/agents/llm-agents.md) and the installed locked SDK are the basis for the advisory integration.
