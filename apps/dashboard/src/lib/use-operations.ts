"use client";

import {useCallback, useEffect, useRef, useState} from "react";
import {api} from "./api";
import type {Deployment, Incident, Metric, Scenario, Service, SystemStatus} from "./types";

export function useOperations() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [metrics, setMetrics] = useState<Metric[]>([]);
  const [services, setServices] = useState<Service[]>([]);
  const [deployments, setDeployments] = useState<Deployment[]>([]);
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [connection, setConnection] = useState("connecting");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const mounted = useRef(false);
  const inFlight = useRef(false);

  const refresh = useCallback(async () => {
    if (inFlight.current) return;
    inFlight.current = true;
    try {
      const [i, m, s, d, st, sc] = await Promise.all([
        api<Incident[]>("/incidents"), api<Metric[]>("/services/orders-api/metrics"),
        api<Service[]>("/services"), api<Deployment[]>("/deployments"),
        api<SystemStatus>("/system/status"), api<Scenario[]>("/demo/scenarios"),
      ]);
      if (!mounted.current) return;
      setIncidents(i); setMetrics(m); setServices(s); setDeployments(d); setStatus(st); setScenarios(sc); setError(null);
    } catch (failure) {
      if (mounted.current) setError(failure instanceof Error ? failure.message : "API connection failed");
    } finally {
      inFlight.current = false;
      if (mounted.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    mounted.current = true;
    const initial = setTimeout(() => void refresh(), 0);
    const source = new EventSource("/api/v1/events");
    let pending: ReturnType<typeof setTimeout> | undefined;
    const update = () => {
      if (pending) clearTimeout(pending);
      pending = setTimeout(() => void refresh(), 100);
    };
    source.addEventListener("connected", () => {setConnection("live"); update();});
    source.addEventListener("update", update);
    source.onerror = () => {setConnection("reconnecting");};
    const poll = setInterval(() => void refresh(), 5000);
    return () => {mounted.current = false; source.close(); clearTimeout(initial); clearInterval(poll); if (pending) clearTimeout(pending);};
  }, [refresh]);

  return {incidents, metrics, services, deployments, status, scenarios, connection, error, loading, refresh};
}
