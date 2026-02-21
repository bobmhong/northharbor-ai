import ReactECharts from "echarts-for-react";
import type { ChartSpec } from "../../types/api";

interface ChartCardProps {
  spec: ChartSpec;
}

export default function ChartCard({ spec }: ChartCardProps) {
  return (
    <div className="card">
      <h3 className="mb-1 text-base font-semibold text-gray-900">
        {spec.title}
      </h3>
      {spec.description && (
        <p className="mb-4 text-sm text-gray-500">{spec.description}</p>
      )}
      <ReactECharts
        option={spec.echarts_option}
        style={{ height: 320, width: "100%" }}
        opts={{ renderer: "canvas" }}
      />
    </div>
  );
}
