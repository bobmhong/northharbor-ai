import ReactECharts from "echarts-for-react";
import type { ChartSpec } from "../../types/api";

interface ChartCardProps {
  spec: ChartSpec;
}

export default function ChartCard({ spec }: ChartCardProps) {
  return (
    <div className="card overflow-hidden">
      <div className="mb-4">
        <h3 className="text-base font-semibold text-harbor-900">
          {spec.title}
        </h3>
        {spec.description && (
          <p className="mt-1 text-sm text-sage-600">{spec.description}</p>
        )}
      </div>
      <div className="rounded-xl bg-sage-50/50 p-2">
        <ReactECharts
          option={spec.echarts_option}
          style={{ height: 320, width: "100%" }}
          opts={{ renderer: "canvas" }}
        />
      </div>
    </div>
  );
}
