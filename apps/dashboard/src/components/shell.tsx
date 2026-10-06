"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import {
  Activity,
  ArrowUpRight,
  Bell,
  Command,
  FileText,
  GitBranch,
  LayoutDashboard,
  Search,
  Server,
  Shield,
  SlidersHorizontal,
  X,
  ChevronDown,
} from "lucide-react";
import { containDialogFocus } from "@/lib/keyboard";
import type { SystemStatus } from "@/lib/types";

const links = [
  { href: "/overview", name: "Overview", icon: LayoutDashboard },
  { href: "/incidents", name: "Incidents", icon: Bell },
  { href: "/services", name: "Services", icon: Server },
  { href: "/metrics", name: "Metrics", icon: Activity },
  { href: "/deployments", name: "Deployments", icon: GitBranch },
  { href: "/postmortems", name: "Postmortems", icon: FileText },
  { href: "/system", name: "System status", icon: SlidersHorizontal },
];
export function Brand() {
  return (
    <>
      <span className="brand-symbol">
        <Shield size={21} strokeWidth={1.7} />
      </span>
      <span>
        sentinel<span className="brand-muted">ops</span>
        <sup> / </sup>
      </span>
    </>
  );
}

export function Shell({
  children,
  section,
  activeCount,
  connection,
  status,
}: {
  children: React.ReactNode;
  section: string;
  activeCount: number;
  connection: string;
  status: SystemStatus | null;
  search?: string;
  setSearch?: (value: string) => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [query, setQuery] = useState("");
  useEffect(() => {
    function key(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key === "k") {
        event.preventDefault();
        dialog.current?.showModal();
        dialog.current?.querySelector("input")?.focus();
      }
    }
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, []);
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      <aside className="sidebar">
        <Link href="/" className="brand" aria-label="SentinelOps home">
          <Brand />
        </Link>
        <Link href="/system" className="workspace">
          <span className="workspace-icon">S</span>
          <div>
            <strong>Sentinel workspace</strong>
            <small>{status?.mode ?? "Connecting"} environment</small>
          </div>
          <ChevronDown size={14} />
        </Link>
        <p className="nav-label">OBSERVE & RESPOND</p>
        <nav aria-label="Main navigation">
          {links.map((item, index) => (
            <Link
              key={item.href}
              href={item.href}
              aria-current={section === item.name ? "page" : undefined}
              className={`nav-link ${section === item.name ? "selected" : ""} ${index === 5 ? "nav-separated" : ""}`}
            >
              <item.icon size={17} />
              <span>{item.name}</span>
              {item.name === "Incidents" && activeCount > 0 && (
                <span className="nav-count">{activeCount}</span>
              )}
            </Link>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="control-note">
            <Shield size={17} />
            <strong>You're in control.</strong>
            <p>
              Evidence before action.
              <br />
              Approval before execution.
            </p>
          </div>
          <div className="engine-status">
            <span
              className={`status-dot ${connection === "live" ? "" : "warning"}`}
            />
            <span>
              {connection === "live"
                ? "Event stream connected"
                : connection === "connecting"
                  ? "Connecting to stream"
                  : "Stream reconnecting"}
            </span>
          </div>
          <a
            href="https://github.com/sohaib-0897/SentinelOps-AI"
            target="_blank"
            rel="noreferrer"
          >
            Documentation <ArrowUpRight size={13} />
          </a>
          <div className="operator">
            <span>SO</span>
            <div>
              <strong>Local operator</strong>
              <small>Operations workspace</small>
            </div>
            <span className="operator-dot" />
          </div>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div className="breadcrumbs">
            <span>Workspace</span>
            <span>/</span>
            <strong>{section}</strong>
          </div>
          <div className="topbar-right">
            <button
              aria-label="Jump to a page"
              className="search-trigger"
              onClick={() => {
                dialog.current?.showModal();
                dialog.current?.querySelector("input")?.focus();
              }}
            >
              <Search size={15} />
              <span>Jump to…</span>
              <kbd>Ctrl K</kbd>
            </button>
            <Link href="/system" className="environment">
              <span
                className={`status-dot ${!status || status.status !== "healthy" ? "warning" : ""}`}
              />
              {status?.mode ?? "CONNECTING"}
            </Link>
          </div>
        </header>
        <main className="content" id="main-content">
          {children}
        </main>
        <footer className="app-footer">
          <span>
            <Shield size={12} /> SentinelOps{" "}
            <span className="muted">/ Evidence first. Human control.</span>
          </span>
          <span>
            {status?.mode ?? "Connecting"} ·{" "}
            {connection === "live" ? "Live event stream" : "Polling every 5s"}
          </span>
        </footer>
      </div>
      <dialog
        ref={dialog}
        onKeyDown={containDialogFocus}
        className="command-dialog"
        aria-labelledby="command-title"
      >
        <div className="dialog-heading">
          <h2 id="command-title">
            <Command size={18} /> Jump to workspace
          </h2>
          <button
            className="button icon-button"
            aria-label="Close navigation"
            onClick={() => dialog.current?.close()}
          >
            <X size={18} />
          </button>
        </div>
        <label className="command-search">
          <Search size={18} />
          <input
            aria-label="Find a page"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Find a page…"
          />
        </label>
        <div className="command-results">
          {links
            .filter((item) =>
              item.name.toLowerCase().includes(query.toLowerCase()),
            )
            .map((item) => (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => dialog.current?.close()}
              >
                <item.icon size={18} />
                {item.name}
                <ArrowUpRight size={15} />
              </Link>
            ))}
          {!links.some((item) =>
            item.name.toLowerCase().includes(query.toLowerCase()),
          ) && <p className="muted">No pages match “{query}”.</p>}
        </div>
        <div className="command-hint">
          Navigate with Tab · Enter to open · Esc to close
        </div>
      </dialog>
    </div>
  );
}
