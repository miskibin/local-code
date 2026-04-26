"use client";

import type { ArtifactChartPayload } from "@/lib/types";

export function ArtifactChart({ payload }: { payload: ArtifactChartPayload }) {
  const data = payload.data ?? [];
  if (data.length === 0) {
    return (
      <div className="px-3.5 py-3 text-center" style={{ color: "var(--ink-3)" }}>
        No data
      </div>
    );
  }
  const max = Math.max(...data.map((d) => d.value));
  const W = 640;
  const H = 240;
  const PAD_L = 40;
  const PAD_B = 36;
  const PAD_T = 16;
  const PAD_R = 16;
  const innerW = W - PAD_L - PAD_R;
  const innerH = H - PAD_T - PAD_B;
  const slot = innerW / data.length;
  const bw = slot * 0.7;
  const gap = slot * 0.3;
  const yTicks = 4;
  const niceMax = Math.ceil(max / 100) * 100 || max;

  return (
    <div className="bg-white px-3.5 py-3">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        width="100%"
        style={{ display: "block", maxHeight: 260 }}
      >
        {Array.from({ length: yTicks + 1 }).map((_, i) => {
          const y = PAD_T + (innerH * i) / yTicks;
          const val = niceMax * (1 - i / yTicks);
          return (
            <g key={i}>
              <line
                x1={PAD_L}
                x2={W - PAD_R}
                y1={y}
                y2={y}
                stroke="var(--border)"
                strokeWidth={1}
              />
              <text
                x={PAD_L - 8}
                y={y + 3}
                textAnchor="end"
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: 10,
                  fill: "var(--ink-3)",
                }}
              >
                {Math.round(val)}
              </text>
            </g>
          );
        })}
        {data.map((d, i) => {
          const h = (d.value / niceMax) * innerH;
          const x = PAD_L + i * (bw + gap) + gap / 2;
          const y = PAD_T + innerH - h;
          return (
            <g key={i}>
              <rect
                x={x}
                y={y}
                width={bw}
                height={h}
                fill="var(--accent)"
                rx={2}
                opacity={0.85}
              />
              <text
                x={x + bw / 2}
                y={H - PAD_B + 14}
                textAnchor="middle"
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: 10,
                  fill: "var(--ink-3)",
                }}
              >
                {d.label}
              </text>
            </g>
          );
        })}
        <line
          x1={PAD_L}
          x2={PAD_L}
          y1={PAD_T}
          y2={PAD_T + innerH}
          stroke="var(--ink-4)"
          strokeWidth={1}
        />
        <line
          x1={PAD_L}
          x2={W - PAD_R}
          y1={PAD_T + innerH}
          y2={PAD_T + innerH}
          stroke="var(--ink-4)"
          strokeWidth={1}
        />
      </svg>
      {payload.caption && (
        <div
          className="mt-1 text-center"
          style={{ fontSize: 11.5, color: "var(--ink-3)" }}
        >
          {payload.caption}
        </div>
      )}
    </div>
  );
}
