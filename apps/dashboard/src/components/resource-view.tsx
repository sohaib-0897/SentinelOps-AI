"use client";
import Link from "next/link";
import { useState } from "react";
import {
  Activity,
  ArrowRight,
  CheckCircle2,
  FileText,
  GitBranch,
  Radio,
  Server,
  ShieldCheck,
} from "lucide-react";
import { clockTime, isActive, label, percent } from "@/lib/api";
import { useOperations } from "@/lib/use-operations";
import { Badge, Empty, Loading, MetricChart, ServiceMap } from "./primitives";
import { Shell } from "./shell";
const descriptions: Record<string, string> = {
  Services:
    "The services under watch. Health, revisions, and the signals behind them.",
  Metrics:
    "Read the signals together. Correlate failures, latency, and resource pressure.",
  Deployments:
    "Every revision leaves a trail. Connect configuration changes to service health.",
  Postmortems: "What happened, how it recovered, and what to improve next.",
  "System status":
    "The control plane, configured providers, and the boundaries of verification.",
};
export function ResourceView({ section }: { section: string }) {
  const data = useOperations();
  const [windowSize, setWindowSize] = useState(0);
  const metrics = windowSize ? data.metrics.slice(-windowSize) : data.metrics;
  const latest = data.metrics.at(-1);
  const postmortems = data.incidents.filter((i) => i.postmortem);
  const active = data.incidents.filter((i) => isActive(i.state));
  const healthy = data.services.filter((s) => s.healthy).length;
  const newest = [...data.deployments].sort((a, b) =>
    b.timestamp.localeCompare(a.timestamp),
  )[0];
  return (
    <Shell
      section={section}
      activeCount={active.length}
      connection={data.connection}
      status={data.status}
    >
      <div className="page-heading">
        <div>
          <div className="eyebrow">OPERATIONS / {section.toUpperCase()}</div>
          <h1>{section}</h1>
          <p>{descriptions[section]}</p>
        </div>
        <span className="live-label">
          <span
            className={`status-dot ${data.connection !== "live" ? "warning" : ""}`}
          />
          {data.connection.toUpperCase()}
        </span>
      </div>
      {data.error && (
        <div className="error-banner" role="alert">
          {data.error}
          <button onClick={() => void data.refresh()}>Retry</button>
        </div>
      )}
      {data.loading && <Loading />}
      {section === "Services" && (
        <>
          <ServiceMap services={data.services} connection={data.connection} />
          <div className="insight-strip">
            <Server size={20} />
            <p>
              <strong>
                {healthy} of {data.services.length} services reporting healthy.
              </strong>{" "}
              {active.length} active investigations in this workspace. Service
              charts show telemetry for the named service only.
            </p>
          </div>
          {!data.services.length && !data.loading && (
            <section className="panel">
              <Empty
                title="No services received"
                description="Check the configured telemetry provider and API connection."
              />
            </section>
          )}
          {data.services.map((service) => {
            const points = data.metrics.filter(
              (m) => m.service_id === service.id,
            );
            const point = points.at(-1);
            return (
              <section className="panel" key={service.id}>
                <div className="panel-heading">
                  <div className="heading-inline">
                    <Server size={18} />
                    <h2>{service.name}</h2>
                  </div>
                  <Badge value={service.healthy ? "healthy" : "degraded"} />
                </div>
                <div className="resource-service">
                  <div>
                    <span>Service ID</span>
                    <strong className="mono">{service.id}</strong>
                  </div>
                  <div>
                    <span>Region</span>
                    <strong>{service.region}</strong>
                  </div>
                  <div>
                    <span>Serving revision</span>
                    <strong className="mono">{service.revision}</strong>
                  </div>
                  <div>
                    <span>Current error rate</span>
                    <strong>{point ? percent(point.error_rate) : "—"}</strong>
                  </div>
                </div>
                <div className="two-columns">
                  <div>
                    <div className="panel-heading">
                      <h2>Error rate</h2>
                    </div>
                    <MetricChart metrics={points} />
                  </div>
                  <div>
                    <div className="panel-heading">
                      <h2>p95 latency</h2>
                    </div>
                    <MetricChart metrics={points} kind="latency_ms" />
                  </div>
                </div>
              </section>
            );
          })}
          <section className="panel">
            <div className="panel-heading">
              <h2>Related investigations</h2>
              <span className="count-pill">{data.incidents.length}</span>
            </div>
            {data.incidents.length ? (
              data.incidents.map((i) => (
                <Link
                  className="resource-incident"
                  href={`/incidents/${i.id}`}
                  key={i.id}
                >
                  <span>{i.title}</span>
                  <Badge value={i.state} />
                  <ArrowRight size={14} />
                </Link>
              ))
            ) : (
              <Empty
                title="No investigations yet"
                description="Service incidents will appear here when a sustained degradation is detected."
              />
            )}
          </section>
        </>
      )}
      {section === "Metrics" && (
        <>
          <div className="registry-toolbar">
            <div className="heading-inline">
              <span className="mono">orders-api</span>
              <span className="badge">{metrics.length} samples</span>
            </div>
            <div
              className="filter-tabs"
              role="group"
              aria-label="Metric sample window"
            >
              {[
                { size: 0, name: "All samples" },
                { size: 30, name: "Last 30" },
                { size: 10, name: "Last 10" },
              ].map((item) => (
                <button
                  key={item.size}
                  className={windowSize === item.size ? "selected" : ""}
                  aria-pressed={windowSize === item.size}
                  onClick={() => setWindowSize(item.size)}
                >
                  {item.name}
                </button>
              ))}
            </div>
          </div>
          <div className="insight-strip">
            <Activity size={20} />
            <p>
              <strong>
                {latest
                  ? latest.error_rate >= 0.05
                    ? "Error rate is above the 5% alert threshold."
                    : "Error rate is below the alert threshold."
                  : "Waiting for telemetry."}
              </strong>{" "}
              {latest
                ? `Latest p95 ${latest.latency_ms.toFixed(0)} ms · DB connections ${percent(latest.db_connections)} utilized. Vertical markers identify observed revision transitions.`
                : "Charts populate from the configured metrics provider."}
            </p>
            <Link href="/deployments" className="button small">
              Revision history <ArrowRight size={13} />
            </Link>
          </div>
          <div className="two-columns">
            {(
              [
                "error_rate",
                "latency_ms",
                "cpu",
                "memory",
                "db_connections",
              ] as const
            ).map((kind) => (
              <section className="panel" key={kind}>
                <div className="panel-heading">
                  <div>
                    <h2 className="capitalize">
                      {kind === "db_connections"
                        ? "Database connection utilization"
                        : kind === "latency_ms"
                          ? "p95 latency"
                          : kind === "cpu"
                            ? "CPU utilization"
                            : label(kind)}
                    </h2>
                    <p>
                      {kind === "error_rate"
                        ? "HTTP failures / total requests"
                        : kind === "latency_ms"
                          ? "95th percentile · recovery target ≤ 200 ms"
                          : "Fraction of available capacity in use"}
                    </p>
                  </div>
                  <span
                    className={`chart-value ${kind === "error_rate" ? "orange" : kind === "latency_ms" ? "violet" : "green"}`}
                  >
                    {latest
                      ? kind === "latency_ms"
                        ? `${latest[kind].toFixed(0)}`
                        : percent(latest[kind])
                      : "—"}
                    {kind === "latency_ms" && <small>ms</small>}
                  </span>
                </div>
                <MetricChart metrics={metrics} kind={kind} />
              </section>
            ))}
            <section className="panel signal-context">
              <div className="panel-heading">
                <div>
                  <h2>Read the window</h2>
                  <p>Summary of the selected telemetry samples</p>
                </div>
                <Activity size={18} className="green" />
              </div>
              {metrics.length ? (
                <>
                  <div className="resource-service">
                    <div>
                      <span>Peak error rate</span>
                      <strong className="orange">
                        {percent(
                          Math.max(...metrics.map((point) => point.error_rate)),
                        )}
                      </strong>
                    </div>
                    <div>
                      <span>Peak p95 latency</span>
                      <strong>
                        {Math.max(
                          ...metrics.map((point) => point.latency_ms),
                        ).toFixed(0)}{" "}
                        ms
                      </strong>
                    </div>
                    <div>
                      <span>First observation</span>
                      <strong className="mono">
                        {clockTime(metrics[0].timestamp)}
                      </strong>
                    </div>
                    <div>
                      <span>Last observation</span>
                      <strong className="mono">
                        {clockTime(metrics[metrics.length - 1].timestamp)}
                      </strong>
                    </div>
                  </div>
                  <div className="panel-body">
                    <p className="muted">
                      {new Set(metrics.map((point) => point.revision)).size}{" "}
                      revisions observed. Compare the deployment markers with
                      error rate, latency, and connection utilization to locate
                      the change in behavior.
                    </p>
                    <Link className="text-link" href="/incidents">
                      Inspect the supporting evidence <ArrowRight size={14} />
                    </Link>
                  </div>
                </>
              ) : (
                <Empty
                  title="Awaiting observations"
                  description="Window summaries appear with the first telemetry samples."
                />
              )}
            </section>
          </div>
        </>
      )}
      {section === "Deployments" && (
        <>
          <div className="stat-grid">
            <div className="stat-card">
              <span>
                Serving revision <GitBranch size={16} />
              </span>
              <strong className="revision-stat">
                {data.services[0]?.revision ?? "—"}
              </strong>
              <small>{data.services[0]?.id ?? "Awaiting service"}</small>
            </div>
            <div className="stat-card">
              <span>
                Observed deployments <GitBranch size={16} />
              </span>
              <strong>
                {data.deployments.length.toString().padStart(2, "0")}
              </strong>
              <small>Retained provider history</small>
            </div>
            <div className="stat-card">
              <span>
                Degraded deployments <Activity size={16} />
              </span>
              <strong className="orange">
                {data.deployments
                  .filter((d) => !d.healthy)
                  .length.toString()
                  .padStart(2, "0")}
              </strong>
              <small>Health recorded at deployment</small>
            </div>
            <div className="stat-card">
              <span>
                Latest observed change <Radio size={16} />
              </span>
              <strong className="revision-stat">
                {newest ? clockTime(newest.timestamp).slice(0, 5) : "—"}
              </strong>
              <small>
                {newest
                  ? new Date(newest.timestamp).toLocaleDateString()
                  : "No deployment events"}
              </small>
            </div>
          </div>
          <div className="two-columns">
            <section className="panel">
              <div className="panel-heading">
                <div>
                  <h2>Change impact · errors</h2>
                  <p>Revision transitions over observed telemetry</p>
                </div>
              </div>
              <MetricChart metrics={data.metrics} />
            </section>
            <section className="panel">
              <div className="panel-heading">
                <div>
                  <h2>Change impact · latency</h2>
                  <p>Compare revision markers across both signals</p>
                </div>
              </div>
              <MetricChart metrics={data.metrics} kind="latency_ms" />
            </section>
          </div>
          <section className="panel">
            <div className="panel-heading">
              <h2>Revision timeline</h2>
              <span className="count-pill">
                {data.deployments.length} events
              </span>
            </div>
            {data.deployments.length ? (
              [...data.deployments]
                .sort((a, b) => b.timestamp.localeCompare(a.timestamp))
                .map((deployment) => (
                  <div className="deployment-row" key={deployment.id}>
                    <div className="deployment-icon">
                      <GitBranch size={18} />
                    </div>
                    <div>
                      <strong>
                        {deployment.previous_revision}{" "}
                        <span className="muted">→</span> {deployment.revision}
                      </strong>
                      <p>
                        {deployment.service_id} ·{" "}
                        {data.services.find(
                          (s) => s.id === deployment.service_id,
                        )?.revision === deployment.revision
                          ? "Currently serving"
                          : "Historical revision"}
                      </p>
                      <div className="config-changes">
                        {Object.entries(deployment.changes).map(
                          ([key, value]) => (
                            <span key={key} className="mono">
                              {key} = {value}
                            </span>
                          ),
                        )}
                      </div>
                    </div>
                    <time
                      title={new Date(deployment.timestamp).toLocaleString()}
                    >
                      {clockTime(deployment.timestamp)}
                    </time>
                    <Badge
                      value={deployment.healthy ? "healthy" : "degraded"}
                    />
                  </div>
                ))
            ) : (
              <Empty
                title="No revision events yet"
                description="Run the bad-deployment scenario from Overview to follow a revision through degradation and recovery."
              />
            )}
            <div className="panel-footnote">
              Deployment badges describe recorded deployment health. Current
              service health is shown on Services.
            </div>
          </section>
        </>
      )}
      {section === "Postmortems" && (
        <>
          <div className="insight-strip">
            <FileText size={21} />
            <p>
              <strong>{postmortems.length} recovery reports.</strong> Each
              report preserves the evidence, response, and lessons from a
              resolved incident.
            </p>
            <Link className="button small" href="/incidents">
              Incident registry <ArrowRight size={13} />
            </Link>
          </div>
          <section className="panel">
            <div className="panel-heading">
              <h2>Recovery reports</h2>
              <span className="count-pill">{postmortems.length}</span>
            </div>
            {postmortems.length ? (
              postmortems.map((incident) => (
                <Link
                  className="postmortem-card"
                  href={`/incidents/${incident.id}?tab=Postmortem`}
                  key={incident.id}
                >
                  <span className="mono green">
                    INC-{incident.id.slice(0, 6).toUpperCase()} /{" "}
                    {incident.service_id}
                  </span>
                  <h3>{incident.title}</h3>
                  <p>{incident.postmortem?.summary}</p>
                  <div>
                    <CheckCircle2 size={14} className="green" />
                    <span>
                      {incident.verification?.recovered
                        ? "Verified recovery"
                        : "Report generated"}
                    </span>
                    <span>
                      · {incident.postmortem?.follow_up_actions.length ?? 0}{" "}
                      follow-up actions
                    </span>
                    <span className="mono">
                      {clockTime(
                        incident.postmortem?.generated_at ??
                          incident.updated_at,
                      )}
                    </span>
                    <ArrowRight size={15} />
                  </div>
                </Link>
              ))
            ) : (
              <Empty
                title="The story continues after recovery"
                description="Complete an incident’s controlled remediation and recovery checks to generate an evidence-backed report."
              />
            )}
          </section>
        </>
      )}
      {section === "System status" && (
        <>
          <div
            className={`health-banner ${data.error || data.status?.status !== "healthy" ? "degraded" : ""}`}
          >
            <span className="health-icon">
              <ShieldCheck size={23} />
            </span>
            <div>
              <strong>
                {data.error
                  ? "Platform connection interrupted"
                  : data.status?.status === "healthy"
                    ? "Control plane operational"
                    : "Checking platform status"}
              </strong>
              <p>
                Mode: {data.status?.mode ?? "connecting"} · Event stream:{" "}
                {data.connection}
              </p>
            </div>
          </div>
          <div className="two-columns">
            <section className="panel">
              <div className="panel-heading">
                <h2>Provider configuration</h2>
                <Badge value={data.status?.mode ?? "connecting"} />
              </div>
              {Object.entries(data.status?.providers ?? {}).map(
                ([name, value]) => (
                  <div className="provider-row" key={name}>
                    <span className="capitalize">{label(name)}</span>
                    <span className="mono">{value}</span>
                    <Badge value="configured" />
                  </div>
                ),
              )}
              <div className="panel-footnote">
                Configuration identifies the selected adapter. It is not an
                independent provider health check.
              </div>
            </section>
            <section className="panel">
              <div className="panel-heading">
                <h2>Connection & execution policy</h2>
                <ShieldCheck size={17} className="green" />
              </div>
              <div className="provider-row">
                <span>Event delivery</span>
                <Badge value={data.connection} />
              </div>
              <div className="provider-row">
                <span>Stream subscribers</span>
                <span className="mono">{data.status?.subscribers ?? "—"}</span>
              </div>
              <div className="provider-row">
                <span>Privileged actions</span>
                <Badge value="approval required" />
              </div>
              <div className="provider-row">
                <span>Cloud integration</span>
                <Badge
                  value={
                    data.status?.cloud_verified ? "verified" : "not verified"
                  }
                />
              </div>
            </section>
          </div>
          <section className="panel">
            <div className="panel-heading">
              <h2>Verification boundaries</h2>
            </div>
            <div className="panel-body">
              <p className="muted">
                Local incident workflows use deterministic scenarios and
                configured telemetry providers. Cloud adapters require separate
                live verification. Real GCP integration is{" "}
                {data.status?.cloud_verified
                  ? "verified"
                  : "awaiting cloud configuration and live verification"}
                .
              </p>
              <p className="muted">
                Remediation tools are allow-listed. Privileged execution
                requires a current approval for the exact incident and action,
                followed by fresh recovery checks.
              </p>
            </div>
          </section>
        </>
      )}
    </Shell>
  );
}
