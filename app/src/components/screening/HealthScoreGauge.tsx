'use client';

import { RadialBarChart, RadialBar, PolarAngleAxis } from 'recharts';
import { scoreBand } from '@/lib/risk';

export function HealthScoreGauge({ score }: { score: number }) {
  const band = scoreBand(score);
  const data = [{ name: 'score', value: score, fill: band.color }];

  return (
    <div className="relative flex h-48 w-48 items-center justify-center">
      <RadialBarChart
        width={192}
        height={192}
        cx={96}
        cy={96}
        innerRadius={62}
        outerRadius={88}
        barSize={16}
        data={data}
        startAngle={210}
        endAngle={-30}
      >
        <PolarAngleAxis type="number" domain={[0, 100]} angleAxisId={0} tick={false} />
        <RadialBar
          dataKey="value"
          cornerRadius={8}
          background={{ fill: 'hsl(var(--muted))' }}
          angleAxisId={0}
        />
      </RadialBarChart>
      <div className="absolute flex flex-col items-center">
        <span className="text-4xl font-bold" style={{ color: band.color }}>
          {score}
        </span>
        <span className="text-xs text-muted-foreground">{band.label}</span>
      </div>
    </div>
  );
}
