import { formatCurrency, formatPercent } from "../../lib/utils";
import type { TableSpec } from "../../types/api";

interface DataTableProps {
  spec: TableSpec;
}

function formatCell(value: unknown, format: string): string {
  if (value == null) return "—";
  if (format === "currency") return formatCurrency(Number(value));
  if (format === "percent") return formatPercent(Number(value));
  if (format === "boolean") return value ? "Yes" : "No";
  if (format === "integer") return Math.round(Number(value)).toString();
  return String(value);
}

export default function DataTable({ spec }: DataTableProps) {
  return (
    <div className="card overflow-hidden p-0">
      <div className="border-b border-sage-200 bg-gradient-to-r from-sage-50 to-white px-6 py-4">
        <h3 className="text-base font-semibold text-harbor-900">{spec.title}</h3>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-sage-200 bg-sage-50/50">
            <tr>
              {spec.columns.map((col) => (
                <th
                  key={col.key}
                  className="px-6 py-3.5 font-semibold text-harbor-700 text-xs uppercase tracking-wider"
                >
                  {col.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-sage-100">
            {spec.rows.map((row, i) => (
              <tr key={i} className="transition-colors hover:bg-sage-50/50">
                {spec.columns.map((col) => (
                  <td key={col.key} className="px-6 py-3.5 text-harbor-800">
                    {formatCell(row[col.key], col.format)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
