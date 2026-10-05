"use client";

import {Area, AreaChart, CartesianGrid, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis} from "recharts";
import {clockTime, label} from "@/lib/api";
import type {Metric} from "@/lib/types";

export function Badge({value}: {value: string}) {
  return <span className={`badge badge-${value.toLowerCase()}`}>{label(value)}</span>;
}

export function Empty({title, description}: {title: string; description: string}) {
  return <div className="empty"><span className="empty-cross">⌁</span><h3>{title}</h3><p>{description}</p></div>;
}

export function MetricChart({metrics, kind = "error_rate", compact = false}: {metrics: Metric[]; kind?: "error_rate" | "latency_ms" | "cpu" | "memory" | "db_connections"; compact?: boolean}) {
  const percent = kind !== "latency_ms";
  const color = kind === "error_rate" ? "#fb9261" : kind === "latency_ms" ? "#8b9dff" : "#53d9a5";
  const data = metrics.map(m => ({time: clockTime(m.timestamp), value: m[kind] * (percent ? 100 : 1)}));
  const id = `fill-${kind}`;
  return <div role="img" aria-label={`${label(kind)} metric history`} className={`chart ${compact ? "chart-compact" : ""}`}>
    <ResponsiveContainer width="100%" height="100%" minWidth={0} initialDimension={{width:500,height:200}}>
      <AreaChart data={data} margin={{top:12,right:12,bottom:0,left:-14}}>
        <defs><linearGradient id={id} x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={color} stopOpacity={.25}/><stop offset="100%" stopColor={color} stopOpacity={0}/></linearGradient></defs>
        <CartesianGrid vertical={false} stroke="#242c38" strokeDasharray="3 5"/>
        <XAxis dataKey="time" tick={{fill:"#7f8b9c",fontSize:10}} axisLine={false} tickLine={false} minTickGap={45}/>
        <YAxis tick={{fill:"#7f8b9c",fontSize:10}} axisLine={false} tickLine={false} tickFormatter={v => `${v}${percent ? "%" : ""}`}/>
        <Tooltip contentStyle={{background:"#161d28",border:"1px solid #303a49",borderRadius:8,color:"#eef2f8"}} formatter={value => [`${Number(value).toFixed(1)}${percent ? "%" : "ms"}`, label(kind)]}/>
        {kind === "error_rate" && <ReferenceLine y={5} stroke="#d96848" strokeDasharray="3 4"/>}
        <Area dataKey="value" stroke={color} fill={`url(#${id})`} strokeWidth={2} isAnimationActive={false}/>
      </AreaChart>
    </ResponsiveContainer>
  </div>;
}
