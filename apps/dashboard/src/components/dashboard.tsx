"use client";

import Link from "next/link";
import { useState } from "react";
import {
  Activity,
  ArrowDownRight,
  ArrowRight,
  CheckCircle2,
  CircleDot,
  Clock3,
  GitBranch,
  ShieldCheck,
  Search,
  TriangleAlert,
} from "lucide-react";
import { clockTime, isActive, label, percent } from "@/lib/api";
import type { Incident } from "@/lib/types";
import { useOperations } from "@/lib/use-operations";
import { Badge, Empty, Loading, MetricChart, ServiceMap } from "./primitives";
import { Shell } from "./shell";
import { DemoControls } from "./demo-controls";

export function IncidentTable({ incidents }: { incidents: Incident[] }) {
  if (!incidents.length)
    return (
      <Empty
        title="No incidents to investigate"
        description="Start a scenario to watch detection, investigation and controlled recovery unfold."
      />
    );
  return (
    <div className="table-scroll">
      <table className="incident-table">
        <thead>
          <tr>
            <th>Incident</th>
            <th>Severity</th>
            <th>Status</th>
            <th>Service</th>
            <th>Detected</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {incidents.map((i) => (
            <tr key={i.id}>
              <td>
                <Link className="incident-link" href={`/incidents/${i.id}`}>
                  <span className="incident-id">
                    INC-{i.id.slice(0, 6).toUpperCase()}
                  </span>
                  <strong>{i.title}</strong>
                  <span className="incident-subline">
                    {i.evidence.length} records ·{" "}
                    {i.root_cause
                      ? label(i.root_cause.cause)
                      : "Diagnosis pending"}
                  </span>
                </Link>
              </td>
              <td>
                <Badge value={i.severity} />
              </td>
              <td>
                <Badge value={i.state} />
              </td>
              <td>
                <span className="mono">{i.service_id}</span>
              </td>
              <td
                className="mono muted"
                title={new Date(i.started_at).toLocaleString()}
              >
                {clockTime(i.started_at)}
                <span className="incident-subline">
                  {new Date(i.started_at).toLocaleDateString([], {
                    month: "short",
                    day: "numeric",
                  })}
                </span>
              </td>
              <td>
                <Link
                  href={`/incidents/${i.id}`}
                  aria-label={`Investigate ${i.title}`}
                >
                  <ArrowRight size={16} />
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function Dashboard({ section = "Overview" }: { section?: string }) {
  const data = useOperations();
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("All");
  const active = data.incidents.filter((i) => isActive(i.state));
  const filtered = data.incidents
    .filter(
      (i) =>
        filter === "All" ||
        (filter === "Active" && isActive(i.state)) ||
        (filter === "Needs approval" && i.state === "AWAITING_APPROVAL") ||
        (filter === "Resolved" && ["RESOLVED", "CLOSED"].includes(i.state)) ||
        (filter === "Needs review" && i.state === "FAILED"),
    )
    .filter((i) =>
      `${i.id} ${i.title} ${i.service_id} ${i.state}`
        .toLowerCase()
        .includes(search.toLowerCase()),
    );
  const latest = data.metrics.at(-1);
  const newest = data.incidents[0];
  const events = data.incidents
    .flatMap((i) => i.timeline.map((e) => ({ ...e, incidentId: i.id })))
    .sort((a, b) => b.timestamp.localeCompare(a.timestamp))
    .slice(0, 6);
  return (
    <Shell
      section={section}
      activeCount={active.length}
      connection={data.connection}
      status={data.status}
    >
      {data.error && (
        <div className="error-banner" role="alert">
          <TriangleAlert size={17} />
          <span>
            API unavailable: {data.error}. Showing last received data.
          </span>
          <button onClick={() => void data.refresh()}>Retry connection</button>
        </div>
      )}
      <div className="page-heading">
        <div>
          <div className="eyebrow">
            <span className="status-dot" />
            OPERATIONS / MISSION CONTROL
          </div>
          <h1>{section === "Overview" ? "Operational overview" : section}</h1>
          <p>The operational picture. The evidence. Your next decision.</p>
        </div>
        <div
          className="heading-meta"
          title={
            latest ? new Date(latest.timestamp).toLocaleString() : undefined
          }
        >
          <Clock3 size={14} />
          <span>
            {latest
              ? `Last sample ${new Date(latest.timestamp).toLocaleDateString([], { month: "short", day: "numeric" })} · ${clockTime(latest.timestamp)}`
              : "Connecting to telemetry"}
          </span>
        </div>
      </div>
      {data.loading && <Loading />}
      {section === "Overview" ? (
        <>
          <DemoControls
            status={data.status}
            scenarios={data.scenarios}
            refresh={data.refresh}
          />
          <div
            className={`health-banner ${active.length || data.error || data.services.some((s) => !s.healthy) ? "degraded" : ""}`}
          >
            <span className="health-icon">
              {active.length ? (
                <TriangleAlert size={22} />
              ) : (
                <ShieldCheck size={22} />
              )}
            </span>
            <div>
              <strong>
                {active.length
                  ? `${active.length} active incident${active.length > 1 ? "s" : ""}. Your attention matters.`
                  : data.loading
                    ? "Connecting to operations"
                    : data.error
                      ? "Telemetry connection interrupted"
                      : data.services.some((s) => !s.healthy)
                        ? "Service degradation observed"
                        : "Systems steady. You’re in control."}
              </strong>
              <p>
                {active.length
                  ? "Review the evidence and authorize the exact recovery plan when you’re ready."
                  : "Monitor observed health, explore an investigation, or run a controlled incident simulation."}
              </p>
            </div>
            {active.length ? (
              <Link
                href={`/incidents/${active[0].id}`}
                className="button health-action"
              >
                Open incident <ArrowRight size={14} />
              </Link>
            ) : (
              <span className="health-chip">
                {data.error || data.loading
                  ? "AWAITING DATA"
                  : data.services.some((s) => !s.healthy)
                    ? "SERVICE DEGRADED"
                    : "UNDER WATCH"}
              </span>
            )}
          </div>
          <div className="stat-grid">
            <div className="stat-card">
              <span>
                Active incidents <TriangleAlert size={16} />
              </span>
              <strong className={active.length ? "orange" : ""}>
                {active.length.toString().padStart(2, "0")}
              </strong>
              <small>
                {data.incidents.filter((i) => i.state === "RESOLVED").length}{" "}
                resolved in this workspace
              </small>
            </div>
            <div className="stat-card">
              <span>
                Service error rate <Activity size={16} />
              </span>
              <strong>{latest ? percent(latest.error_rate) : "—"}</strong>
              <small
                className={
                  latest && latest.error_rate >= 0.05 ? "orange" : "green"
                }
              >
                <CircleDot size={10} />{" "}
                {!latest
                  ? "Awaiting samples"
                  : latest.error_rate >= 0.05
                    ? "Above 5% alert threshold"
                    : "Within healthy range"}
              </small>
            </div>
            <div className="stat-card">
              <span>
                p95 latency <Clock3 size={16} />
              </span>
              <strong>
                {latest ? Math.round(latest.latency_ms) : "—"}
                <em>ms</em>
              </strong>
              <small>Target &lt; 200ms</small>
            </div>
            <div className="stat-card">
              <span>
                Current revision <GitBranch size={16} />
              </span>
              <strong className="revision-stat">
                {data.services[0]?.revision ?? "—"}
              </strong>
              <small>
                {data.deployments.length} deployment events observed
              </small>
            </div>
          </div>
          <div className="two-columns">
            <section className="panel">
              <div className="panel-heading">
                <div>
                  <h2>Error rate</h2>
                  <p>HTTP failures · orders-api</p>
                </div>
                <span className="chart-value orange">
                  {latest ? percent(latest.error_rate) : "—"}
                </span>
              </div>
              <MetricChart metrics={data.metrics} />
            </section>
            <section className="panel">
              <div className="panel-heading">
                <div>
                  <h2>Response latency</h2>
                  <p>p95 duration · milliseconds</p>
                </div>
                <span className="chart-value violet">
                  {latest?.latency_ms.toFixed(0) ?? "—"}
                  <small>ms</small>
                </span>
              </div>
              <MetricChart metrics={data.metrics} kind="latency_ms" />
            </section>
          </div>
          <section className="panel">
            <div className="panel-heading">
              <div className="heading-inline">
                <h2>Incident command</h2>
                <span className="count-pill">{data.incidents.length}</span>
              </div>
              <Link className="text-link" href="/incidents">
                View all incidents <ArrowRight size={13} />
              </Link>
            </div>
            <IncidentTable incidents={filtered.slice(0, 4)} />
          </section>
          <ServiceMap services={data.services} connection={data.connection} />

          <div className="two-columns bottom-grid">
            <section className="panel">
              <div className="panel-heading">
                <h2>Investigation activity</h2>
                <span className="live-label">
                  <span
                    className={`status-dot ${data.connection === "live" ? "" : "warning"}`}
                  />
                  {data.connection === "live" ? "LIVE" : "RECONNECTING"}
                </span>
              </div>
              {events.length ? (
                <div className="activity-list">
                  {events.map((e) => (
                    <Link
                      href={`/incidents/${e.incidentId}`}
                      key={e.id}
                      className="activity-row"
                    >
                      <span
                        className={`activity-marker ${e.kind === "agent" ? "agent" : ""}`}
                      >
                        {e.kind === "agent" ? (
                          <CircleDot size={13} />
                        ) : (
                          <CheckCircle2 size={13} />
                        )}
                      </span>
                      <div>
                        <span className="activity-actor">{e.actor}</span>
                        <p>{e.message}</p>
                      </div>
                      <time>{clockTime(e.timestamp)}</time>
                    </Link>
                  ))}
                </div>
              ) : (
                <Empty
                  title="Agents standing by"
                  description="Activity appears here as an incident is detected."
                />
              )}
            </section>
            <section className="panel">
              <div className="panel-heading">
                <h2>Service health</h2>
                <Link className="text-link" href="/services">
                  Services <ArrowRight size={13} />
                </Link>
              </div>
              {data.services.map((s) => (
                <div className="service-row" key={s.id}>
                  <span
                    className={`service-indicator ${s.healthy ? "" : "unhealthy"}`}
                  >
                    <Activity size={18} />
                  </span>
                  <div>
                    <strong>{s.name}</strong>
                    <p className="mono">
                      {s.id} · {s.region}
                    </p>
                  </div>
                  <Badge value={s.healthy ? "healthy" : "degraded"} />
                </div>
              ))}
              <div className="service-footnote">
                <ArrowDownRight size={15} />
                <span>
                  {newest?.root_cause
                    ? `${percent(newest.root_cause.confidence)} evidence score · ${label(newest.root_cause.cause)}`
                    : "Evidence-backed diagnosis will appear after investigation."}
                </span>
              </div>
            </section>
          </div>
        </>
      ) : (
        <>
          <div className="stat-grid">
            <div className="stat-card">
              <span>
                Active response <TriangleAlert size={16} />
              </span>
              <strong className="orange">
                {active.length.toString().padStart(2, "0")}
              </strong>
              <small>Investigations in progress</small>
            </div>
            <div className="stat-card">
              <span>
                Awaiting your approval <ShieldCheck size={16} />
              </span>
              <strong>
                {data.incidents
                  .filter((i) => i.state === "AWAITING_APPROVAL")
                  .length.toString()
                  .padStart(2, "0")}
              </strong>
              <small>Exact plans ready for review</small>
            </div>
            <div className="stat-card">
              <span>
                Verified recoveries <CheckCircle2 size={16} />
              </span>
              <strong className="green">
                {data.incidents
                  .filter((i) => i.verification?.recovered)
                  .length.toString()
                  .padStart(2, "0")}
              </strong>
              <small>Confirmed by fresh telemetry</small>
            </div>
            <div className="stat-card">
              <span>
                Operator review <CircleDot size={16} />
              </span>
              <strong>
                {data.incidents
                  .filter((i) => i.state === "FAILED")
                  .length.toString()
                  .padStart(2, "0")}
              </strong>
              <small>Investigations needing intervention</small>
            </div>
          </div>
          <div className="registry-toolbar">
            <div
              className="filter-tabs"
              role="group"
              aria-label="Filter incidents"
            >
              {[
                "All",
                "Active",
                "Needs approval",
                "Resolved",
                "Needs review",
              ].map((name) => (
                <button
                  key={name}
                  aria-pressed={filter === name}
                  className={filter === name ? "selected" : ""}
                  onClick={() => setFilter(name)}
                >
                  {name}
                </button>
              ))}
            </div>
            <label className="registry-search">
              <Search size={15} />
              <input
                aria-label="Search incidents"
                placeholder="Search title, service, or ID…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </label>
          </div>
          <section className="panel">
            <div className="panel-heading">
              <h2>Incident registry</h2>
              <span className="count-pill">{filtered.length} records</span>
            </div>
            {filtered.length ? (
              <IncidentTable incidents={filtered} />
            ) : (
              <Empty
                title={
                  search || filter !== "All"
                    ? "No matching incidents"
                    : "No incidents to investigate"
                }
                description={
                  search || filter !== "All"
                    ? "Try a different filter or clear your search to see other incidents."
                    : "Run a simulation to follow detection, investigation, and controlled recovery."
                }
              />
            )}
            <div className="registry-summary">
              <span>
                <strong>{data.incidents.length}</strong> total incidents
              </span>
              <span>
                <strong>{active.length}</strong> active
              </span>
              <span>Ordered by detection time</span>
            </div>
          </section>
          <DemoControls
            status={data.status}
            scenarios={data.scenarios}
            refresh={data.refresh}
          />
        </>
      )}
    </Shell>
  );
}
