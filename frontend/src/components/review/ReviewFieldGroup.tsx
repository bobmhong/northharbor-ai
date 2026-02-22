import ReviewField from "./ReviewField";
import type { FieldConfig } from "./fieldConfig";

interface ReviewFieldGroupProps {
  title: string;
  fields: FieldConfig[];
  planData: Record<string, unknown>;
  onSave: (path: string, value: unknown) => Promise<void>;
}

function resolveValue(data: Record<string, unknown>, path: string): unknown {
  const segments = path.split(".");
  let current: unknown = data;
  for (const seg of segments) {
    if (current == null || typeof current !== "object") return undefined;
    current = (current as Record<string, unknown>)[seg];
  }
  if (current != null && typeof current === "object" && "value" in (current as Record<string, unknown>)) {
    return (current as Record<string, unknown>).value;
  }
  return current;
}

function isCollected(data: Record<string, unknown>, path: string): boolean {
  const segments = path.split(".");
  let current: unknown = data;
  for (const seg of segments) {
    if (current == null || typeof current !== "object") return false;
    current = (current as Record<string, unknown>)[seg];
  }
  if (current == null) return false;
  if (typeof current === "object" && "confidence" in (current as Record<string, unknown>)) {
    const pf = current as Record<string, unknown>;
    return Number(pf.confidence) > 0 || pf.source !== "default";
  }
  return true;
}

export default function ReviewFieldGroup({ title, fields, planData, onSave }: ReviewFieldGroupProps) {
  const visibleFields = fields.filter((f) => isCollected(planData, f.path));
  if (visibleFields.length === 0) return null;

  return (
    <div className="card">
      <h3 className="text-sm font-semibold text-harbor-700 uppercase tracking-wider mb-2">{title}</h3>
      <div>
        {visibleFields.map((field) => (
          <ReviewField
            key={field.path}
            config={field}
            value={resolveValue(planData, field.path)}
            onSave={onSave}
          />
        ))}
      </div>
    </div>
  );
}
