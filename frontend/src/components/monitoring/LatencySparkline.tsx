import type { Telemetry } from "../../types";

/** Tiny latency trend for the last heartbeats. Red dots mark heartbeats that reported "down". */
export function LatencySparkline({ points, threshold }: { points: Telemetry[]; threshold: number }) {
  const w = 240, h = 48, pad = 4;
  if (points.length < 2) return <div className="spark-empty">Waiting for heartbeats…</div>;
  const max = Math.max(threshold * 1.4, ...points.map((p) => p.latency_ms));
  const x = (i: number) => pad + (i / (points.length - 1)) * (w - 2 * pad);
  const y = (v: number) => h - pad - (v / max) * (h - 2 * pad);
  const d = points.map((p, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(p.latency_ms).toFixed(1)}`).join(" ");
  const last = points[points.length - 1];
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="spark" role="img"
         aria-label={`Latency trend, last ${last.latency_ms} ms, threshold ${threshold} ms`}>
      <line x1={pad} x2={w - pad} y1={y(threshold)} y2={y(threshold)} className="spark-threshold" />
      <path d={d} className="spark-line" />
      {points.map((p, i) => p.reported_status === "down"
        ? <circle key={i} cx={x(i)} cy={y(0)} r={2.5} className="spark-down" /> : null)}
    </svg>
  );
}
