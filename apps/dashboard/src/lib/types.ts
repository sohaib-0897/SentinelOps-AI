export type State = "DETECTED" | "TRIAGING" | "INVESTIGATING" | "DIAGNOSED" | "AWAITING_APPROVAL" | "REMEDIATING" | "VERIFYING" | "RESOLVED" | "FAILED" | "CLOSED";
export type Risk = "READ_ONLY" | "LOW_RISK" | "PRIVILEGED";
export interface Metric {timestamp: string; service_id: string; error_rate: number; latency_ms: number; cpu: number; memory: number; db_connections: number; requests: number; revision: string}
export interface Service {id: string; name: string; region: string; revision: string; healthy: boolean}
export interface Deployment {id: string; service_id: string; revision: string; previous_revision: string; timestamp: string; changes: Record<string,string>; healthy: boolean}
export interface IncidentEvent {id: string; timestamp: string; kind: string; actor: string; message: string; data: Record<string,unknown>}
export interface Evidence {id: string; source: string; summary: string; timestamp: string; data: Record<string,unknown>}
export interface Hypothesis {id: string; cause: string; description: string; confidence: number; supporting_evidence: string[]; contradicting_evidence: string[]; timestamp: string}
export interface RootCause {hypothesis_id: string; cause: string; confidence: number; explanation: string; evidence_ids: string[]}
export interface Historical {id: string; title: string; signature: string; cause: string; remediation: string; outcome: string; similarity: number}
export interface Action {id: string; capability: string; service_id: string; risk: Risk; parameters: Record<string,string>}
export interface Plan {id: string; summary: string; actions: Action[]; status: "proposed" | "approved" | "executing" | "executed" | "failed"; created_at: string; expires_at: string}
export interface Verification {recovered: boolean; samples: number; before_error_rate: number; after_error_rate: number; before_latency_ms: number; after_latency_ms: number; regression_detected: boolean; checks: Record<string, boolean>; timestamp: string}
export interface Postmortem {summary: string; impact: string; timeline: IncidentEvent[]; root_cause: string; detection: string; response: string; remediation: string; what_worked: string[]; what_failed: string[]; prevention: string[]; follow_up_actions: string[]; generated_at: string}
export interface Incident {id: string; title: string; service_id: string; severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"; state: State; started_at: string; updated_at: string; resolved_at: string | null; version: number; symptoms: string[]; evidence: Evidence[]; hypotheses: Hypothesis[]; root_cause: RootCause | null; historical_matches: Historical[]; remediation: Plan | null; approvals: {id: string; actor: string; timestamp: string}[]; verification: Verification | null; postmortem: Postmortem | null; timeline: IncidentEvent[]; tool_calls: string[]}
export interface SystemStatus {status: string; mode: string; demo_mode: boolean; providers: Record<string,string>; demo: {scenario: string | null; paused: boolean; step: number; speed: number; error: string | null}; subscribers: number; cloud_verified: boolean}
export interface Scenario {name: string; title: string}
