"use client";

import Link from "next/link";
import {Activity, ArrowUpRight, Bell, Boxes, FileText, GitBranch, LayoutDashboard, Radio, Search, Server, Shield, SlidersHorizontal} from "lucide-react";
import type {SystemStatus} from "@/lib/types";

const links = [
  {href:"/",name:"Overview",icon:LayoutDashboard}, {href:"/incidents",name:"Incidents",icon:Bell},
  {href:"/services",name:"Services",icon:Server}, {href:"/metrics",name:"Metrics",icon:Activity},
  {href:"/deployments",name:"Deployments",icon:GitBranch}, {href:"/postmortems",name:"Postmortems",icon:FileText},
  {href:"/system",name:"System status",icon:SlidersHorizontal},
];

export function Shell({children, section, activeCount, connection, status, search, setSearch}: {children: React.ReactNode; section: string; activeCount: number; connection: string; status: SystemStatus | null; search?: string; setSearch?: (value: string) => void}) {
  return <div className="app-shell">
    <aside className="sidebar">
      <Link href="/" className="brand"><span className="brand-symbol"><Shield size={23}/></span><span>sentinel<span className="brand-muted">ops</span><sup>AI</sup></span></Link>
      <div className="workspace"><span className="workspace-icon"><Boxes size={17}/></span><div><strong>Operations workspace</strong><small>{status?.mode ?? "local"} environment</small></div><span className="workspace-chevron">⌄</span></div>
      <p className="nav-label">WORKSPACE</p>
      <nav aria-label="Main navigation">{links.map(item => <Link key={item.href} href={item.href} className={`nav-link ${section === item.name ? "selected" : ""}`}><item.icon size={17}/><span>{item.name}</span>{item.name === "Incidents" && activeCount > 0 && <span className="nav-count">{activeCount}</span>}</Link>)}</nav>
      <div className="sidebar-bottom"><div className="engine-status"><span className={`status-dot ${connection === "live" ? "" : "warning"}`}/><span>{connection === "live" ? "Event stream connected" : "Reconnecting stream"}</span></div><p>Evidence first. Human control.</p><a href="https://github.com/sohaib-0897/SentinelOps-AI" target="_blank" rel="noreferrer">Project documentation <ArrowUpRight size={13}/></a><div className="operator"><span>SO</span><div><strong>Local operator</strong><small>SRE workspace</small></div><span className="operator-dot"/></div></div>
    </aside>
    <div className="main-shell">
      <header className="topbar"><div className="breadcrumbs">Workspace <span>/</span> <strong>{section}</strong></div><div className="topbar-right">{setSearch && <label className="search"><Search size={15}/><input aria-label="Search incidents" placeholder="Search incidents…" value={search} onChange={e => setSearch(e.target.value)}/><kbd>/</kbd></label>}<span className="environment"><span className="status-dot"/>{status?.mode ?? "LOCAL"}</span><Radio size={17} className="muted"/></div></header>
      <main className="content">{children}</main>
      <footer className="app-footer"><span>SentinelOps AI <span className="muted">/ Incident command</span></span><span>Local telemetry · {connection === "live" ? "Live SSE" : "Polling fallback"}</span></footer>
    </div>
  </div>;
}
