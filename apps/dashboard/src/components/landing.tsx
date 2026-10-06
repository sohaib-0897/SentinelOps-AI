"use client";
import Link from "next/link";
import { useState } from "react";
import {
  Activity,
  ArrowDown,
  ArrowRight,
  ArrowUpRight,
  Check,
  FileSearch,
  Fingerprint,
  GitBranch,
  LockKeyhole,
  Radar,
  ShieldCheck,
} from "lucide-react";
import { navigateTabs } from "@/lib/keyboard";
import { Brand } from "./shell";
import { Badge, MetricChart } from "./primitives";
import { useOperations } from "@/lib/use-operations";
import { isActive, percent } from "@/lib/api";

const workflow = [
  {
    name: "Detect",
    title: "Catch the signal. Keep the context.",
    description:
      "Sustained degradation creates an incident with the service, revision, and observed symptoms attached. Transient noise stays out of the response loop.",
    icon: Radar,
    detail: "Metrics + sustained thresholds → incident",
  },
  {
    name: "Investigate",
    title: "A diagnosis you can interrogate.",
    description:
      "Correlate logs, metrics, deployments, and historical incidents. Compare ranked hypotheses against their supporting and contradicting source records.",
    icon: FileSearch,
    detail: "Source records → ranked hypotheses → diagnosis",
  },
  {
    name: "Approve",
    title: "Your infrastructure. Your decision.",
    description:
      "Review the exact target, parameters, and risk before authorizing a remediation plan. An evidence score never grants permission to change a service.",
    icon: LockKeyhole,
    detail: "Exact action + current approval → controlled execution",
  },
  {
    name: "Verify",
    title: "Recovery is measured, not assumed.",
    description:
      "Fresh telemetry, clean logs, and service checks confirm recovery. The incident closes with a factual postmortem and concrete follow-up actions.",
    icon: ShieldCheck,
    detail: "Five fresh samples → verified recovery → postmortem",
  },
];
export function Landing() {
  const [step, setStep] = useState(0);
  const data = useOperations();
  const latest = data.metrics.at(-1);
  const active = data.incidents.filter((i) => isActive(i.state));
  const selected = workflow[step];
  return (
    <div className="landing">
      <a className="skip-link" href="#landing-main">
        Skip to content
      </a>
      <header className="landing-nav">
        <Link className="brand" href="/" aria-label="SentinelOps home">
          <Brand />
        </Link>
        <nav aria-label="Product navigation">
          <a href="#workflow">How it works</a>
          <a href="#platform">The platform</a>
          <a
            href="https://github.com/sohaib-0897/SentinelOps-AI"
            target="_blank"
            rel="noreferrer"
          >
            GitHub <ArrowUpRight size={13} />
          </a>
        </nav>
        <Link href="/overview" className="button nav-cta">
          Open workspace <ArrowUpRight size={15} />
        </Link>
      </header>
      <main id="landing-main">
        <section className="landing-hero">
          <div className="hero-copy">
            <div className="eyebrow">
              <span className="status-dot" /> INCIDENT INTELLIGENCE. OPERATOR
              CONTROL.
            </div>
            <h1>
              When systems break,
              <br />
              find your <span>signal.</span>
            </h1>
            <p>
              From the first alert to verified recovery.
              <br />
              Investigate with evidence. Act with confidence.
              <br />
              Keep every critical decision in human hands.
            </p>
            <div className="hero-actions">
              <Link className="button primary" href="/overview">
                Enter mission control <ArrowUpRight size={18} />
              </Link>
              <a href="#workflow" className="text-link">
                Explore the workflow <ArrowDown size={15} />
              </a>
            </div>
            <div className="hero-assurance">
              <ShieldCheck size={14} /> Evidence first <span /> Approval gated{" "}
              <span /> Fully traceable
            </div>
          </div>
          <div
            className="signal-visual"
            aria-label="Conceptual signal diagram: telemetry is correlated into evidence and passed through a human approval gate"
            role="img"
          >
            <div className="orbit orbit-one" />
            <div className="orbit orbit-two" />
            <div className="orbit orbit-three" />
            <div className="signal-grid" />
            <svg viewBox="0 0 580 520" aria-hidden="true">
              <path
                className="signal-path dim"
                d="M0 140H120L220 240H300L400 140H580M0 380H120L220 280H300L420 400H580"
              />
              <path
                className="signal-path"
                d="M0 260H100L130 260L150 230L170 295L195 250H265L290 260H360L390 260L415 200L440 315L465 260H580"
              />
              <circle cx="290" cy="260" r="70" />
              <circle cx="290" cy="260" r="91" className="signal-ring" />
            </svg>
            <div className="signal-core">
              <Fingerprint size={55} strokeWidth={1} />
            </div>
            <span className="signal-label sl-one">01 / OBSERVE</span>
            <span className="signal-label sl-two">02 / CORRELATE</span>
            <span className="signal-label sl-three">03 / RESPOND</span>
            <div className="signal-tag tag-one">
              <Activity size={14} />
              <span>
                Telemetry in.<small>Context preserved.</small>
              </span>
            </div>
            <div className="signal-tag tag-two">
              <LockKeyhole size={15} />
              <span>
                Human approval<small>Before every privileged action.</small>
              </span>
            </div>
            <span className="signal-coordinate">S / OPS — CONTROL PLANE</span>
          </div>
        </section>
        <div className="landing-principles">
          <span>
            BUILT FOR THE MOMENT
            <br />
            EVERY SECOND MATTERS
          </span>
          <strong>
            <Radar size={19} />
            Detect degradation
          </strong>
          <strong>
            <FileSearch size={19} />
            Explain the cause
          </strong>
          <strong>
            <LockKeyhole size={19} />
            Control the response
          </strong>
          <strong>
            <ShieldCheck size={19} />
            Prove recovery
          </strong>
        </div>
        <section className="landing-section" id="platform">
          <div className="section-title">
            <div>
              <div className="eyebrow">01 / THE OPERATIONAL PICTURE</div>
              <h2>
                Everything connected.
                <br />
                <span>Nothing left to guess.</span>
              </h2>
            </div>
            <p>
              Service health, revision history, and active investigations. One
              workspace to understand what changed and what needs you next.
            </p>
          </div>
          <div className="product-preview">
            <div className="preview-toolbar">
              <span>
                <span className="status-dot" /> SENTINELOPS / MISSION CONTROL
              </span>
              <span>
                {data.error
                  ? "Telemetry unavailable"
                  : data.loading
                    ? "Connecting…"
                    : `${data.status?.mode ?? "local"} workspace · actual telemetry`}
              </span>
              <Link href="/overview">
                Open workspace <ArrowUpRight size={15} />
              </Link>
            </div>
            <div className="preview-content">
              <div className="preview-summary">
                <div className="eyebrow">OPERATIONAL OVERVIEW</div>
                <h3>
                  {data.loading
                    ? "Establishing connection."
                    : data.error
                      ? "Waiting for your signal."
                      : active.length
                        ? "Attention where it matters."
                        : "A clear view of your systems."}
                </h3>
                <div className="preview-kpis">
                  <div>
                    <strong>
                      {data.loading || data.error
                        ? "—"
                        : active.length.toString().padStart(2, "0")}
                    </strong>
                    <span>Active incidents</span>
                  </div>
                  <div>
                    <strong>{latest ? percent(latest.error_rate) : "—"}</strong>
                    <span>Service error rate</span>
                  </div>
                  <div>
                    <strong>
                      {latest ? Math.round(latest.latency_ms) : "—"}
                      <small> ms</small>
                    </strong>
                    <span>p95 latency</span>
                  </div>
                </div>
                <div className="preview-services">
                  {data.services.map((service) => (
                    <div key={service.id}>
                      <span className="mono">{service.id}</span>
                      <Badge value={service.healthy ? "healthy" : "degraded"} />
                    </div>
                  ))}
                </div>
              </div>
              <div className="preview-chart">
                <div className="panel-heading">
                  <h2>Every change leaves a signal.</h2>
                  <GitBranch size={16} />
                </div>
                <MetricChart metrics={data.metrics} />
              </div>
            </div>
          </div>
        </section>
        <section className="landing-section workflow-section" id="workflow">
          <div className="section-title">
            <div>
              <div className="eyebrow">02 / FROM SIGNAL TO RESOLUTION</div>
              <h2>
                One incident.
                <br />
                <span>A complete chain of evidence.</span>
              </h2>
            </div>
            <p>
              Automation does the investigation.
              <br />
              You stay in command of the response.
            </p>
          </div>
          <div
            className="workflow-tabs"
            role="tablist"
            tabIndex={-1}
            onKeyDown={navigateTabs}
            aria-label="Explore incident workflow"
          >
            {workflow.map((item, index) => (
              <button
                id={`workflow-tab-${index}`}
                aria-controls="workflow-panel"
                role="tab"
                aria-selected={step === index}
                tabIndex={step === index ? 0 : -1}
                onClick={() => setStep(index)}
                key={item.name}
                className={step === index ? "selected" : ""}
              >
                <span>0{index + 1}</span>
                <item.icon size={20} />
                {item.name}
                <ArrowRight size={16} />
              </button>
            ))}
          </div>
          <div
            id="workflow-panel"
            role="tabpanel"
            aria-labelledby={`workflow-tab-${step}`}
            className="workflow-content"
          >
            <div className="workflow-glyph">
              <selected.icon size={72} strokeWidth={1} />
              <span>0{step + 1}</span>
            </div>
            <div>
              <div className="eyebrow">
                {selected.name.toUpperCase()} / SENTINELOPS WORKFLOW
              </div>
              <h3>{selected.title}</h3>
              <p>{selected.description}</p>
              <div className="workflow-detail">
                <Check size={15} />
                {selected.detail}
              </div>
            </div>
          </div>
        </section>
        <section className="landing-section capability-section">
          <div className="section-title">
            <div>
              <div className="eyebrow">03 / TRUST IS A DESIGN REQUIREMENT</div>
              <h2>
                Built to explain.
                <br />
                <span>Designed to be accountable.</span>
              </h2>
            </div>
          </div>
          <div className="capability-grid">
            {[
              {
                icon: FileSearch,
                title: "Every claim has a source.",
                text: "Inspect the records behind a diagnosis. Supporting evidence, contradictions, and historical matches remain visible.",
              },
              {
                icon: LockKeyhole,
                title: "No invisible decisions.",
                text: "Review the exact remediation plan, risk, and scope. Privileged actions require a current, explicit approval.",
              },
              {
                icon: ShieldCheck,
                title: "A closed loop, on record.",
                text: "Verify the effect of a change with new telemetry. Keep the full timeline, audit trail, and postmortem together.",
              },
            ].map((item, index) => (
              <article key={item.title}>
                <div>
                  <item.icon size={26} strokeWidth={1.4} />
                  <span>0{index + 1}</span>
                </div>
                <h3>{item.title}</h3>
                <p>{item.text}</p>
              </article>
            ))}
          </div>
        </section>
        <section className="landing-cta">
          <div className="eyebrow">LESS UNCERTAINTY. MORE CONTROL.</div>
          <h2>
            Your next incident.
            <br />
            <span>Handled with clarity.</span>
          </h2>
          <p>
            Run a local incident simulation. Follow the evidence.
            <br />
            Approve the recovery. See the entire story.
          </p>
          <Link className="button primary" href="/overview">
            Launch the workspace <ArrowUpRight size={18} />
          </Link>
          <span className="cta-note">
            Local demo available · No cloud account required
          </span>
        </section>
      </main>
      <footer className="landing-footer">
        <Link href="/" className="brand">
          <Brand />
        </Link>
        <span>Evidence first. Human control.</span>
        <a
          href="https://github.com/sohaib-0897/SentinelOps-AI"
          target="_blank"
          rel="noreferrer"
        >
          Explore the source <ArrowUpRight size={15} />
        </a>
      </footer>
    </div>
  );
}
