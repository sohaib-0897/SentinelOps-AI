"use client";

import { useId } from "react";
import {
  Activity,
  Database,
  FileSearch,
  LockKeyhole,
  Radio,
  Server,
  ShieldCheck,
} from "lucide-react";
import Link from "next/link";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { clockTime, label } from "@/lib/api";
import type { Incident, Metric, Service } from "@/lib/types";

export function Badge({ value }: { value: string }) {
  return (
    <span className={`badge badge-${value.toLowerCase()}`}>{label(value)}</span>
  );
}
export function Empty({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="empty">
      <span className="empty-cross">
        <Activity size={25} />
      </span>
      <h3>{title}</h3>
      <p>{description}</p>
    </div>
  );
}
export function Loading() {
  return (
    <div
      className="loading-grid"
      role="status"
      aria-label="Loading operational data"
    >
      <span>Connecting to operational data…</span>
      {[0, 1, 2].map((i) => (
        <div className="skeleton" key={i} />
      ))}
    </div>
  );
}

export function MetricChart({
  metrics,
  kind = "error_rate",
  compact = false,
}: {
  metrics: Metric[];
  kind?: "error_rate" | "latency_ms" | "cpu" | "memory" | "db_connections";
  compact?: boolean;
}) {
  const id = useId().replaceAll(":", "");
  const percentage = kind !== "latency_ms";
  const color =
    kind === "error_rate"
      ? "#f49b82"
      : kind === "latency_ms"
        ? "#b5acf2"
        : "#c2ef85";
  const data = metrics.map((m) => ({
    time: new Date(m.timestamp).getTime(),
    value: m[kind] * (percentage ? 100 : 1),
    revision: m.revision,
  }));
  const transitions = data.filter(
    (m, index) => index > 0 && m.revision !== data[index - 1].revision,
  );
  if (!data.length)
    return (
      <Empty
        title="Awaiting telemetry"
        description="Observed samples and revision transitions will appear here."
      />
    );
  return (
    <>
      <div
        role="img"
        aria-label={`${label(kind)} metric history, ${data.length} samples, latest ${data.at(-1)?.value.toFixed(1)} ${percentage ? "percent" : "milliseconds"}`}
        className={`chart ${compact ? "chart-compact" : ""}`}
      >
        <ResponsiveContainer
          width="100%"
          height="100%"
          minWidth={0}
          initialDimension={{ width: 500, height: 200 }}
        >
          <AreaChart
            data={data}
            margin={{ top: 20, right: 25, bottom: 0, left: 0 }}
          >
            <defs>
              <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={color} stopOpacity={0.18} />
                <stop offset="100%" stopColor={color} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid
              vertical={false}
              stroke="#2b302d"
              strokeDasharray="2 5"
            />
            <XAxis
              dataKey="time"
              type="number"
              domain={["dataMin", "dataMax"]}
              tickFormatter={(v) => clockTime(new Date(v).toISOString())}
              tick={{ fill: "#8b948e", fontSize: 10 }}
              axisLine={false}
              tickLine={false}
              minTickGap={35}
              tickCount={4}
            />
            <YAxis
              width={47}
              tick={{ fill: "#8b948e", fontSize: 10 }}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v) => `${v}${percentage ? "%" : ""}`}
            />
            <Tooltip
              labelFormatter={(v) =>
                clockTime(new Date(Number(v)).toISOString())
              }
              contentStyle={{
                background: "#1b201c",
                border: "1px solid #414a40",
                borderRadius: 8,
                color: "#f3f3e9",
                fontSize: 12,
              }}
              formatter={(value) => [
                `${Number(value).toFixed(1)}${percentage ? "%" : " ms"}`,
                label(kind),
              ]}
            />
            {kind === "error_rate" && (
              <ReferenceLine
                y={5}
                stroke="#ab715d"
                strokeDasharray="4 5"
                label={{
                  value: "5% alert",
                  fill: "#c99a84",
                  fontSize: 9,
                  position: "insideTopRight",
                }}
              />
            )}
            {kind === "latency_ms" && (
              <ReferenceLine
                y={200}
                stroke="#77708b"
                strokeDasharray="4 5"
                label={{
                  value: "200 ms target",
                  fill: "#aaa2c4",
                  fontSize: 9,
                  position: "insideTopRight",
                }}
              />
            )}
            {transitions.map((event, index) => (
              <ReferenceLine
                key={`${event.time}-${index}`}
                x={event.time}
                stroke="#a1b293"
                strokeDasharray="3 4"
                label={{
                  value: event.revision,
                  position: "insideTopRight",
                  fill: "#b2bca8",
                  fontSize: 9,
                }}
              />
            ))}
            <Area
              type="linear"
              dataKey="value"
              stroke={color}
              fill={`url(#${id})`}
              strokeWidth={2}
              isAnimationActive={false}
              activeDot={{ r: 4, stroke: "#111510", strokeWidth: 2 }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
      {!compact && (
        <div className="chart-legend">
          <span>
            <i style={{ background: color }} />
            {label(kind)} {kind === "db_connections" ? "utilization" : ""}
          </span>
          <span>
            {transitions.length
              ? `${transitions.length} revision transitions`
              : "No revision transition in window"}
          </span>
          <span>{data.length} samples</span>
        </div>
      )}
    </>
  );
}
const stages = [
  { name: "Detected", icon: Radio },
  { name: "Investigating", icon: FileSearch },
  { name: "Approval", icon: LockKeyhole },
  { name: "Recovery", icon: ShieldCheck },
];
export function Lifecycle({ incident }: { incident: Incident }) {
  const state = incident.state;
  const current = ["RESOLVED", "CLOSED"].includes(state)
    ? 4
    : ["VERIFYING", "REMEDIATING"].includes(state)
      ? 3
      : state === "AWAITING_APPROVAL"
        ? 2
        : state === "DETECTED"
          ? 0
          : 1;
  return (
    <ol className="lifecycle" aria-label="Incident progression">
      {stages.map((stage, index) => (
        <li
          key={stage.name}
          className={`${index < current ? "complete" : ""} ${index === current ? "current" : ""}`}
          aria-current={index === current ? "step" : undefined}
        >
          <stage.icon size={16} />
          <div>
            <span>0{index + 1}</span>
            <strong>{stage.name}</strong>
          </div>
          <small>
            {index < current
              ? "Complete"
              : index === current
                ? state === "FAILED"
                  ? "Needs review"
                  : "In progress"
                : "Pending"}
          </small>
        </li>
      ))}
    </ol>
  );
}
export function ServiceMap({
  services,
  connection,
}: {
  services: Service[];
  connection: string;
}) {
  return (
    <section className="panel topology-panel">
      <div className="panel-heading">
        <div>
          <h2>Operational topology</h2>
          <p>Observed services → evidence → controlled response</p>
        </div>
        <span className="count-pill">
          {services.length} service{services.length !== 1 ? "s" : ""}
        </span>
      </div>
      <div className="topology">
        <div className="topology-services">
          {services.length ? (
            services.map((service) => (
              <Link
                href="/services"
                className={`topology-node ${service.healthy ? "" : "affected"}`}
                key={service.id}
              >
                <Server size={22} />
                <strong>{service.id}</strong>
                <small>
                  {service.revision} · {service.region}
                </small>
                <Badge value={service.healthy ? "healthy" : "degraded"} />
              </Link>
            ))
          ) : (
            <div className="topology-node">
              <Server size={22} />
              <strong>No services received</strong>
              <small>Awaiting provider data</small>
            </div>
          )}
        </div>
        <span className="topology-wire" />
        <Link href="/metrics" className="topology-node">
          <Database size={22} />
          <strong>Telemetry</strong>
          <small>Metrics · logs · revisions</small>
          <span className="live-label">
            {connection === "live" ? "STREAM CONNECTED" : "STREAM CONNECTING"}
          </span>
        </Link>
        <span className="topology-wire" />
        <Link href="/incidents" className="topology-node accent-node">
          <ShieldCheck size={22} />
          <strong>Incident command</strong>
          <small>Investigate → approve → verify</small>
          <span className="live-label">HUMAN CONTROL</span>
        </Link>
      </div>
      <div className="panel-footnote">
        Logical operations flow. Service nodes reflect the configured provider;
        connectors do not imply network dependencies.
      </div>
    </section>
  );
}
