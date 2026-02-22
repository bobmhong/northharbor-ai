import { useState, useEffect, useRef, useCallback, type ReactNode } from "react";
import { cn } from "../../lib/utils";

export interface CrossFieldWarning {
  rule_id: string;
  fields: string[];
  message: string;
  suggestion: string;
}

interface WarningsPanelProps {
  warnings: CrossFieldWarning[];
  onFieldClick?: (fieldPath: string) => void;
}

const FIELD_LABELS: Record<string, string> = {
  "social_security.combined_at_67_monthly": "SS at 67",
  "social_security.combined_at_70_monthly": "SS at 70",
  "client.birth_year": "Birth year",
  "client.retirement_window": "Retirement age",
  "monte_carlo.horizon_age": "Horizon age",
  "accounts.employee_contribution_percent": "Your contribution",
  "accounts.employer_match_percent": "Employer match",
  "spending.retirement_monthly_real": "Monthly spending",
  "income.current_gross_annual": "Annual income",
  "retirement_philosophy.legacy_goal_total_real": "Legacy goal",
  "accounts.retirement_balance": "Retirement balance",
};

function formatRuleName(ruleId: string): string {
  return ruleId
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function getFieldLabel(fieldPath: string): string {
  return (
    FIELD_LABELS[fieldPath] ??
    fieldPath.split(".").pop()?.replace(/_/g, " ") ??
    fieldPath
  );
}

function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(() =>
    typeof window !== "undefined" ? window.matchMedia(query).matches : false,
  );

  useEffect(() => {
    const mql = window.matchMedia(query);
    const handler = (e: MediaQueryListEvent) => setMatches(e.matches);
    mql.addEventListener("change", handler);
    return () => mql.removeEventListener("change", handler);
  }, [query]);

  return matches;
}

function WarningIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
      />
    </svg>
  );
}

function PanelHeader({
  count,
  onClose,
  closeIcon,
}: {
  count: number;
  onClose: () => void;
  closeIcon: ReactNode;
}) {
  return (
    <div className="flex items-center justify-between px-4 py-3 bg-white border-b border-sage-200">
      <div className="flex items-center gap-2">
        <WarningIcon className="h-5 w-5 text-amber-500" />
        <span className="text-sm font-semibold text-harbor-800">Warnings</span>
        <span className="flex items-center justify-center h-5 min-w-[20px] bg-amber-500 text-white rounded-full text-xs font-bold px-1">
          {count}
        </span>
      </div>
      <button
        type="button"
        onClick={onClose}
        className="p-1 rounded-md text-sage-400 hover:text-harbor-700 hover:bg-sage-100 transition-colors duration-150"
        aria-label="Close warnings panel"
      >
        {closeIcon}
      </button>
    </div>
  );
}

function WarningCards({
  warnings,
  onFieldClick,
}: {
  warnings: CrossFieldWarning[];
  onFieldClick?: (fieldPath: string) => void;
}) {
  return (
    <div className="flex flex-col gap-3">
      {warnings.map((w) => (
        <div
          key={w.rule_id}
          className="bg-amber-50 border border-amber-200 rounded-lg p-3"
        >
          <p className="text-xs font-semibold text-amber-800">
            {formatRuleName(w.rule_id)}
          </p>
          <p className="mt-1 text-sm text-amber-900">{w.message}</p>
          <p className="mt-1 text-xs text-amber-600/80">{w.suggestion}</p>
          {w.fields.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1.5">
              {w.fields.map((field) => (
                <button
                  key={field}
                  type="button"
                  onClick={() => onFieldClick?.(field)}
                  className="bg-sage-100 text-sage-700 rounded-full px-2 py-0.5 text-xs cursor-pointer hover:bg-sage-200 transition-colors duration-150"
                >
                  {getFieldLabel(field)}
                </button>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

const CHEVRON_RIGHT = (
  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
  </svg>
);

const CLOSE_X = (
  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
  </svg>
);

export default function WarningsPanel({
  warnings,
  onFieldClick,
}: WarningsPanelProps) {
  const isDesktop = useMediaQuery("(min-width: 1024px)");
  const [collapsed, setCollapsed] = useState(true);
  const [drawerMounted, setDrawerMounted] = useState(false);
  const [drawerVisible, setDrawerVisible] = useState(false);
  const [shouldPulse, setShouldPulse] = useState(false);
  const prevCountRef = useRef(0);
  const closeTimerRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  useEffect(() => {
    setCollapsed(!isDesktop);
    setDrawerMounted(false);
    setDrawerVisible(false);
  }, [isDesktop]);

  useEffect(() => {
    if (warnings.length > 0 && prevCountRef.current === 0) {
      setShouldPulse(true);
      const timer = setTimeout(() => setShouldPulse(false), 2000);
      return () => clearTimeout(timer);
    }
    prevCountRef.current = warnings.length;
  }, [warnings.length]);

  useEffect(() => {
    return () => {
      if (closeTimerRef.current) clearTimeout(closeTimerRef.current);
    };
  }, []);

  // Close mobile drawer on Escape
  useEffect(() => {
    if (!drawerMounted) return;
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") closeDrawer();
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  });

  const openDrawer = useCallback(() => {
    if (closeTimerRef.current) clearTimeout(closeTimerRef.current);
    setDrawerMounted(true);
    requestAnimationFrame(() => {
      requestAnimationFrame(() => setDrawerVisible(true));
    });
  }, []);

  const closeDrawer = useCallback(() => {
    setDrawerVisible(false);
    closeTimerRef.current = setTimeout(() => setDrawerMounted(false), 300);
  }, []);

  if (warnings.length === 0) return null;

  const badge = (
    <button
      type="button"
      onClick={() => (isDesktop ? setCollapsed((c) => !c) : openDrawer())}
      className={cn(
        "flex items-center justify-center h-10 w-10 bg-amber-500 text-white rounded-full shadow-elevated text-sm font-bold",
        "transition-all duration-300 ease-in-out hover:bg-amber-600",
        shouldPulse && "animate-pulse",
      )}
      aria-label={`${warnings.length} validation warning${warnings.length !== 1 ? "s" : ""}`}
    >
      {warnings.length}
    </button>
  );

  if (isDesktop) {
    return (
      <div
        className={cn(
          "transition-all duration-300 ease-in-out flex-shrink-0 overflow-hidden",
          collapsed ? "w-14" : "w-[300px]",
        )}
      >
        {collapsed ? (
          <div className="flex justify-center pt-4">{badge}</div>
        ) : (
          <div className="h-full flex flex-col border-l border-sage-200 bg-white shadow-elevated">
            <PanelHeader
              count={warnings.length}
              onClose={() => setCollapsed(true)}
              closeIcon={CHEVRON_RIGHT}
            />
            <div className="flex-1 overflow-y-auto p-4">
              <WarningCards warnings={warnings} onFieldClick={onFieldClick} />
            </div>
          </div>
        )}
      </div>
    );
  }

  return (
    <>
      <div className="fixed bottom-6 right-6 z-40">{badge}</div>

      {drawerMounted && (
        <div className="fixed inset-0 z-50 flex flex-col justify-end">
          <div
            className={cn(
              "absolute inset-0 bg-harbor-900/40 backdrop-blur-sm transition-opacity duration-300",
              drawerVisible ? "opacity-100" : "opacity-0",
            )}
            onClick={closeDrawer}
            aria-hidden="true"
          />
          <div
            className={cn(
              "relative max-h-[70vh] flex flex-col bg-white rounded-t-2xl shadow-elevated",
              "transition-transform duration-300 ease-in-out",
              drawerVisible ? "translate-y-0" : "translate-y-full",
            )}
            role="dialog"
            aria-label="Validation warnings"
          >
            <div className="flex justify-center pt-3 pb-1">
              <div className="w-10 h-1 rounded-full bg-sage-300" />
            </div>
            <PanelHeader
              count={warnings.length}
              onClose={closeDrawer}
              closeIcon={CLOSE_X}
            />
            <div className="flex-1 overflow-y-auto p-4">
              <WarningCards warnings={warnings} onFieldClick={onFieldClick} />
            </div>
          </div>
        </div>
      )}
    </>
  );
}
