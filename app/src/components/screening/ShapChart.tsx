'use client';

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
  ReferenceLine,
} from 'recharts';

export function ShapChart({ values }: { values: Record<string, number> }) {
  const data = Object.entries(values)
    .map(([feature, value]) => ({ feature, value }))
    .sort((a, b) => Math.abs(b.value) - Math.abs(a.value));

  if (data.length === 0) {
    return <p className="text-sm text-muted-foreground">No feature attributions available.</p>;
  }

  return (
    <ResponsiveContainer width="100%" height={Math.max(200, data.length * 34)}>
      <BarChart data={data} layout="vertical" margin={{ left: 24, right: 24 }}>
        <XAxis type="number" tickFormatter={(v) => v.toFixed(2)} stroke="hsl(var(--muted-foreground))" />
        <YAxis
          type="category"
          dataKey="feature"
          width={140}
          stroke="hsl(var(--muted-foreground))"
          tick={{ fontSize: 12 }}
        />
        <Tooltip
          formatter={(v: number) => [v.toFixed(4), 'SHAP value']}
          contentStyle={{ borderRadius: 8, fontSize: 12 }}
        />
        <ReferenceLine x={0} stroke="hsl(var(--border))" />
        <Bar dataKey="value" radius={[0, 4, 4, 0]}>
          {data.map((d) => (
            <Cell key={d.feature} fill={d.value >= 0 ? '#ef4444' : '#10b981'} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
