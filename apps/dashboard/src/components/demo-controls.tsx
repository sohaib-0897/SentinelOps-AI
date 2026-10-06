"use client";

import { useState } from "react";
import {
  FastForward,
  FlaskConical,
  Pause,
  Play,
  RotateCcw,
} from "lucide-react";
import { api } from "@/lib/api";
import type { Scenario, SystemStatus } from "@/lib/types";

export function DemoControls({
  status,
  scenarios,
  refresh,
}: {
  status: SystemStatus | null;
  scenarios: Scenario[];
  refresh: () => Promise<void>;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [scenario, setScenario] = useState("bad-deployment");
  async function run(path: string, body: unknown) {
    setBusy(true);
    setError(null);
    try {
      await api(path, body);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Control failed");
    } finally {
      setBusy(false);
    }
  }
  if (!status?.demo_mode) return null;
  return (
    <div className="demo-wrapper">
      <div className="demo-controls">
        <div className="demo-intro">
          <FlaskConical size={17} />
          <strong>Incident simulator</strong>
          <span>Safe, deterministic telemetry</span>
        </div>
        <div className="demo-actions">
          <select
            aria-label="Failure scenario"
            value={scenario}
            onChange={(e) => setScenario(e.target.value)}
          >
            {scenarios.length ? (
              scenarios.map((s) => (
                <option key={s.name} value={s.name}>
                  {s.title}
                </option>
              ))
            ) : (
              <option value="bad-deployment">bad-deployment</option>
            )}
          </select>
          <button
            className="button primary small"
            disabled={busy}
            onClick={() => void run("/demo/start", { scenario })}
          >
            <Play size={13} />
            Start Demo
          </button>
          <button
            className="button small"
            disabled={busy || !status?.demo.scenario}
            onClick={() => void run("/demo/pause", {})}
          >
            <Pause size={13} />
            {status?.demo.paused ? "Resume" : "Pause"}
          </button>
          <button
            className="button icon-button"
            aria-label="Restart demo"
            title="Restart demo, retaining previous incident"
            disabled={busy}
            onClick={() => void run("/demo/start", { scenario, restart: true })}
          >
            <RotateCcw size={14} />
          </button>
          <button
            className="button small"
            disabled={busy}
            onClick={() =>
              void run("/demo/speed", {
                speed: status?.demo.speed === 10 ? 1 : 10,
              })
            }
          >
            <FastForward size={14} />
            {status?.demo.speed === 10 ? "10×" : "Speed Up"}
          </button>
          <button
            className="button small"
            disabled={busy}
            onClick={() => void run("/demo/start", { scenario, restart: true })}
          >
            Inject Failure
          </button>
        </div>
      </div>
      {error && (
        <div className="inline-error" role="alert">
          {error}
        </div>
      )}
    </div>
  );
}
