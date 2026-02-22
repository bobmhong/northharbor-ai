import { useCallback, useEffect, useRef, useState } from "react";
import type { FieldConfig } from "./fieldConfig";

interface ReviewFieldProps {
  config: FieldConfig;
  value: unknown;
  onSave: (path: string, value: unknown) => Promise<void>;
}

function formatDisplay(value: unknown, type: FieldConfig["type"]): string {
  if (value == null || value === 0) return "—";
  switch (type) {
    case "currency": {
      const num = Number(value);
      return isNaN(num) ? String(value) : num.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
    }
    case "percentage": {
      const num = Number(value);
      if (isNaN(num)) return String(value);
      return num <= 1 ? `${(num * 100).toFixed(0)}%` : `${num.toFixed(0)}%`;
    }
    case "boolean":
      return value === true || value === "yes" ? "Yes" : value === false || value === "no" ? "No" : String(value);
    case "age_range": {
      const range = value as { min?: number; max?: number } | null;
      if (!range) return "—";
      return range.min === range.max ? String(range.min) : `${range.min}–${range.max}`;
    }
    default:
      return String(value);
  }
}

function parseEditValue(raw: string, type: FieldConfig["type"]): unknown {
  const trimmed = raw.trim().replace(/[$,%]/g, "").replace(/,/g, "");
  switch (type) {
    case "currency":
    case "number":
      return trimmed === "" ? 0 : Number(trimmed);
    case "percentage":
      return trimmed === "" ? 0 : Number(trimmed) / 100;
    default:
      return raw.trim();
  }
}

function toEditString(value: unknown, type: FieldConfig["type"]): string {
  if (value == null) return "";
  switch (type) {
    case "currency":
      return String(Number(value) || "");
    case "percentage": {
      const num = Number(value);
      return isNaN(num) ? "" : String(num <= 1 ? Math.round(num * 100) : Math.round(num));
    }
    case "number":
      return String(Number(value) || "");
    default:
      return String(value);
  }
}

export default function ReviewField({ config, value, onSave }: ReviewFieldProps) {
  const [editing, setEditing] = useState(false);
  const [editValue, setEditValue] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (editing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [editing]);

  useEffect(() => {
    if (saved) {
      const t = setTimeout(() => setSaved(false), 1500);
      return () => clearTimeout(t);
    }
  }, [saved]);

  const startEdit = useCallback(() => {
    if (config.type === "boolean") return;
    setEditValue(toEditString(value, config.type));
    setEditing(true);
    setError(null);
  }, [value, config.type]);

  const commitEdit = useCallback(async () => {
    setEditing(false);
    const parsed = parseEditValue(editValue, config.type);
    const currentVal = config.type === "percentage" && typeof value === "number" && value <= 1
      ? Math.round(value * 100)
      : value;
    const newVal = config.type === "percentage" && typeof parsed === "number"
      ? Math.round(parsed * 100)
      : parsed;
    if (String(newVal) === String(currentVal)) return;

    setSaving(true);
    setError(null);
    try {
      await onSave(config.path, parsed);
      setSaved(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }, [editValue, config, value, onSave]);

  const handleBooleanToggle = useCallback(async (newValue: boolean) => {
    setSaving(true);
    setError(null);
    try {
      await onSave(config.path, newValue);
      setSaved(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }, [config.path, onSave]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === "Enter") commitEdit();
    if (e.key === "Escape") setEditing(false);
  }, [commitEdit]);

  if (config.type === "boolean") {
    const isYes = value === true || value === "yes";
    return (
      <div className="flex items-center justify-between py-3 px-1 border-b border-sage-100 last:border-0">
        <span className="text-sm text-sage-700">{config.label}</span>
        <div className="flex items-center gap-2">
          {error && <span className="text-xs text-red-500">{error}</span>}
          {saved && <span className="text-xs text-emerald-600">Saved</span>}
          <div className="flex rounded-lg overflow-hidden border border-sage-200">
            <button
              type="button"
              className={`px-3 py-1 text-xs font-medium transition-colors ${isYes ? "bg-harbor-500 text-white" : "bg-white text-sage-600 hover:bg-sage-50"}`}
              onClick={() => handleBooleanToggle(true)}
              disabled={saving}
            >
              Yes
            </button>
            <button
              type="button"
              className={`px-3 py-1 text-xs font-medium transition-colors ${!isYes ? "bg-harbor-500 text-white" : "bg-white text-sage-600 hover:bg-sage-50"}`}
              onClick={() => handleBooleanToggle(false)}
              disabled={saving}
            >
              No
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (config.type === "age_range") {
    const range = (value as { min?: number; max?: number } | null) ?? { min: 65, max: 67 };
    return (
      <AgeRangeField
        config={config}
        range={range}
        onSave={onSave}
        saved={saved}
        setSaved={setSaved}
        error={error}
        setError={setError}
      />
    );
  }

  return (
    <div className="flex items-center justify-between py-3 px-1 border-b border-sage-100 last:border-0">
      <span className="text-sm text-sage-700">{config.label}</span>
      <div className="flex items-center gap-2">
        {error && <span className="text-xs text-red-500">{error}</span>}
        {saved && !editing && <span className="text-xs text-emerald-600">Saved</span>}
        {saving && <span className="text-xs text-sage-400">Saving...</span>}
        {editing ? (
          <div className="flex items-center gap-1">
            {config.type === "currency" && <span className="text-sm text-sage-400">$</span>}
            <input
              ref={inputRef}
              type={config.type === "text" ? "text" : "number"}
              className="input-field w-32 text-sm py-1 px-2 text-right"
              value={editValue}
              onChange={(e) => setEditValue(e.target.value)}
              onBlur={commitEdit}
              onKeyDown={handleKeyDown}
              min={config.min}
              max={config.max}
              aria-label={config.label}
            />
            {config.type === "percentage" && <span className="text-sm text-sage-400">%</span>}
          </div>
        ) : (
          <button
            type="button"
            className="group flex items-center gap-1.5 rounded-lg px-2 py-1 text-sm font-medium text-harbor-800 transition-colors hover:bg-sage-100"
            onClick={startEdit}
          >
            <span>{formatDisplay(value, config.type)}</span>
            <svg className="h-3.5 w-3.5 text-sage-400 opacity-0 group-hover:opacity-100 transition-opacity" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
            </svg>
          </button>
        )}
      </div>
    </div>
  );
}

function AgeRangeField({
  config,
  range,
  onSave,
  saved,
  setSaved,
  error,
  setError,
}: {
  config: FieldConfig;
  range: { min?: number; max?: number };
  onSave: (path: string, value: unknown) => Promise<void>;
  saved: boolean;
  setSaved: (v: boolean) => void;
  error: string | null;
  setError: (v: string | null) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [minVal, setMinVal] = useState(String(range.min ?? 65));
  const [maxVal, setMaxVal] = useState(String(range.max ?? 67));
  const [saving, setSaving] = useState(false);

  const commitEdit = useCallback(async () => {
    setEditing(false);
    const newMin = Number(minVal) || 60;
    const newMax = Number(maxVal) || 70;
    if (newMin === range.min && newMax === range.max) return;

    setSaving(true);
    setError(null);
    try {
      await onSave(config.path, { min: Math.min(newMin, newMax), max: Math.max(newMin, newMax) });
      setSaved(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }, [minVal, maxVal, range, config.path, onSave, setError, setSaved]);

  return (
    <div className="flex items-center justify-between py-3 px-1 border-b border-sage-100 last:border-0">
      <span className="text-sm text-sage-700">{config.label}</span>
      <div className="flex items-center gap-2">
        {error && <span className="text-xs text-red-500">{error}</span>}
        {saved && !editing && <span className="text-xs text-emerald-600">Saved</span>}
        {saving && <span className="text-xs text-sage-400">Saving...</span>}
        {editing ? (
          <div className="flex items-center gap-1">
            <input
              type="number"
              className="input-field w-16 text-sm py-1 px-2 text-center"
              value={minVal}
              onChange={(e) => setMinVal(e.target.value)}
              onBlur={commitEdit}
              onKeyDown={(e) => { if (e.key === "Enter") commitEdit(); if (e.key === "Escape") setEditing(false); }}
              min={55}
              max={80}
              aria-label={`${config.label} minimum`}
            />
            <span className="text-sage-400">–</span>
            <input
              type="number"
              className="input-field w-16 text-sm py-1 px-2 text-center"
              value={maxVal}
              onChange={(e) => setMaxVal(e.target.value)}
              onBlur={commitEdit}
              onKeyDown={(e) => { if (e.key === "Enter") commitEdit(); if (e.key === "Escape") setEditing(false); }}
              min={55}
              max={80}
              aria-label={`${config.label} maximum`}
            />
          </div>
        ) : (
          <button
            type="button"
            className="group flex items-center gap-1.5 rounded-lg px-2 py-1 text-sm font-medium text-harbor-800 transition-colors hover:bg-sage-100"
            onClick={() => {
              setMinVal(String(range.min ?? 65));
              setMaxVal(String(range.max ?? 67));
              setEditing(true);
            }}
          >
            <span>{formatDisplay(range, "age_range")}</span>
            <svg className="h-3.5 w-3.5 text-sage-400 opacity-0 group-hover:opacity-100 transition-opacity" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
            </svg>
          </button>
        )}
      </div>
    </div>
  );
}
