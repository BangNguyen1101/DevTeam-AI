import { formatCompact } from '@/lib/format'

/** Dependency-free SVG charts sized by their container width. */

export function LineChart({
  points,
  height = 220,
  series,
}: {
  points: { label: string; values: number[] }[]
  height?: number
  series: { name: string; color: string; format?: (n: number) => string }[]
}) {
  const width = 640
  const pad = { top: 16, right: 16, bottom: 28, left: 44 }
  const innerW = width - pad.left - pad.right
  const innerH = height - pad.top - pad.bottom
  // Each series is normalised to its own max so tokens and $ share one plot
  const maxes = series.map((_, i) => Math.max(...points.map((p) => p.values[i]), 0) || 1)
  const x = (i: number) => pad.left + (points.length === 1 ? innerW / 2 : (i / (points.length - 1)) * innerW)
  const y = (v: number, s: number) => pad.top + innerH - (v / maxes[s]) * innerH

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="h-auto w-full" role="img">
      {[0, 0.25, 0.5, 0.75, 1].map((t) => (
        <g key={t}>
          <line x1={pad.left} x2={width - pad.right} y1={pad.top + innerH * (1 - t)} y2={pad.top + innerH * (1 - t)} stroke="rgb(255 255 255 / 0.06)" />
          <text x={pad.left - 8} y={pad.top + innerH * (1 - t) + 4} textAnchor="end" className="fill-outline font-mono text-[10px]">
            {formatCompact(maxes[0] * t)}
          </text>
        </g>
      ))}
      {series.map((s, si) => {
        const path = points.map((p, i) => `${i ? 'L' : 'M'}${x(i)},${y(p.values[si], si)}`).join(' ')
        const area = `${path} L${x(points.length - 1)},${pad.top + innerH} L${x(0)},${pad.top + innerH} Z`
        return (
          <g key={s.name}>
            <path d={area} fill={s.color} opacity={0.08} />
            <path d={path} fill="none" stroke={s.color} strokeWidth={2} />
            {points.map((p, i) => (
              <circle key={i} cx={x(i)} cy={y(p.values[si], si)} r={3} fill={s.color}>
                <title>{`${p.label} · ${s.name}: ${(s.format ?? formatCompact)(p.values[si])}`}</title>
              </circle>
            ))}
          </g>
        )
      })}
      {points.map((p, i) => (
        <text key={p.label} x={x(i)} y={height - 8} textAnchor="middle" className="fill-outline font-mono text-[10px]">
          {p.label}
        </text>
      ))}
    </svg>
  )
}

export function Donut({ parts, size = 120, label }: { parts: { value: number; color: string }[]; size?: number; label?: React.ReactNode }) {
  const total = parts.reduce((s, p) => s + p.value, 0)
  const r = 42
  const c = 2 * Math.PI * r
  let offset = 0
  return (
    <div className="relative shrink-0" style={{ width: size, height: size }}>
      <svg viewBox="0 0 100 100" className="size-full -rotate-90">
        <circle cx="50" cy="50" r={r} fill="none" stroke="#31353e" strokeWidth="10" />
        {total > 0 &&
          parts.map((p, i) => {
            const len = (p.value / total) * c
            const el = (
              <circle key={i} cx="50" cy="50" r={r} fill="none" stroke={p.color} strokeWidth="10" strokeDasharray={`${len} ${c - len}`} strokeDashoffset={-offset} />
            )
            offset += len
            return el
          })}
      </svg>
      {label && <div className="absolute inset-0 flex flex-col items-center justify-center text-center">{label}</div>}
    </div>
  )
}

export function Ring({ value, size = 140, children }: { value: number; size?: number; children?: React.ReactNode }) {
  const r = 42
  const c = 2 * Math.PI * r
  return (
    <div className="relative shrink-0" style={{ width: size, height: size }}>
      <svg viewBox="0 0 100 100" className="size-full -rotate-90">
        <circle cx="50" cy="50" r={r} fill="none" stroke="#31353e" strokeWidth="7" />
        <circle cx="50" cy="50" r={r} fill="none" stroke="#adc6ff" strokeWidth="7" strokeLinecap="round" strokeDasharray={`${(value / 100) * c} ${c}`} />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center text-center">{children}</div>
    </div>
  )
}
