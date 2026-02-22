import { useEffect, useState } from "react";
import { Link, Outlet, useLocation } from "react-router-dom";
import { cn } from "../../lib/utils";
import { usePlan, usePlans, useUpdateScenarioName } from "../../api/hooks";
import EditScenarioModal from "./EditScenarioModal";
import logoCropped from "../../../../logo-cropped.jpeg";

const NAV_ITEMS = [
  { path: "/plans", label: "Plans" },
];

const BREADCRUMB_MAP: Record<string, { label: string; parent?: string }> = {
  "/plans": { label: "Your Plans" },
  "/interview": { label: "Interview", parent: "/plans" },
  "/dashboard": { label: "Dashboard", parent: "/plans" },
  "/report": { label: "Report", parent: "/plans" },
};

function getBreadcrumbs(pathname: string) {
  const crumbs: { path: string; label: string }[] = [];
  
  let matchedPath = Object.keys(BREADCRUMB_MAP).find(p => pathname.startsWith(p));
  if (!matchedPath) matchedPath = "/plans";
  
  const entry = BREADCRUMB_MAP[matchedPath];
  if (entry?.parent) {
    const parentEntry = BREADCRUMB_MAP[entry.parent];
    if (parentEntry) {
      crumbs.push({ path: entry.parent, label: parentEntry.label });
    }
  }
  crumbs.push({ path: pathname, label: entry?.label || "Page" });
  
  return crumbs;
}

function extractPlanId(pathname: string, search: string): string | undefined {
  const dashboardMatch = pathname.match(/^\/dashboard\/([^/]+)/);
  if (dashboardMatch) return dashboardMatch[1];
  
  const reportMatch = pathname.match(/^\/report\/([^/]+)/);
  if (reportMatch) return reportMatch[1];
  
  if (pathname.startsWith("/interview")) {
    const params = new URLSearchParams(search);
    return params.get("plan_id") ?? undefined;
  }
  
  return undefined;
}

export default function Layout() {
  const location = useLocation();
  const breadcrumbs = getBreadcrumbs(location.pathname);
  const [showEditScenario, setShowEditScenario] = useState(false);
  
  const planId = extractPlanId(location.pathname, location.search);
  const { data: plan } = usePlan(planId);
  const { data: allPlans } = usePlans();
  const updateScenarioName = useUpdateScenarioName();
  
  const planData = plan as Record<string, unknown> | undefined;
  const clientObj = planData?.client as Record<string, unknown> | undefined;
  const nameField = clientObj?.name as Record<string, unknown> | undefined;
  const clientName = typeof nameField?.value === "string" ? nameField.value : null;
  const scenarioName = typeof planData?.scenario_name === "string" ? planData.scenario_name : null;

  const existingScenarioNames = (allPlans ?? [])
    .filter((p) => p.client_name === (clientName || "Client") && p.plan_id !== planId)
    .map((p) => p.scenario_name);

  async function handleUpdateScenarioName(newName: string) {
    if (!planId) return;
    try {
      await updateScenarioName.mutateAsync({ planId, scenarioName: newName });
      setShowEditScenario(false);
    } catch {
      // Error is handled by the mutation
    }
  }

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "instant" });
  }, [location.pathname]);

  return (
    <>
      <EditScenarioModal
        isOpen={showEditScenario}
        onClose={() => setShowEditScenario(false)}
        onConfirm={handleUpdateScenarioName}
        existingNames={existingScenarioNames}
        currentName={scenarioName || "Default"}
        isPending={updateScenarioName.isPending}
        error={updateScenarioName.error?.message}
      />
      <div className="min-h-screen flex flex-col bg-gradient-subtle">
      <header className="sticky top-0 z-50 header-gradient shrink-0">
        <div className="mx-auto flex h-16 sm:h-20 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
          <Link to="/" className="group flex items-center gap-3 sm:gap-4 shrink-0">
            <div className="logo-container">
              <img
                src={logoCropped}
                alt="NorthHarbor Sage"
                className="h-10 sm:h-12 md:h-14 w-auto object-contain transition-all duration-300 group-hover:scale-[1.02]"
              />
            </div>
            <div className="hidden md:block border-l border-sage-300/50 pl-4">
              <p className="text-xs font-medium text-harbor-600 tracking-wide uppercase">
                Retirement Planning
              </p>
              <p className="text-[10px] text-sage-500 mt-0.5">
                Your financial future, simplified
              </p>
            </div>
          </Link>

          <nav className="flex items-center gap-1 sm:gap-2">
            {NAV_ITEMS.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                className={cn(
                  "relative rounded-lg sm:rounded-xl px-2.5 sm:px-4 py-2 text-xs sm:text-sm font-semibold transition-all duration-200",
                  location.pathname.startsWith(item.path)
                    ? "bg-white/90 text-harbor-700 shadow-card ring-1 ring-harbor-200/40"
                    : "text-harbor-700 hover:bg-white/60 hover:text-harbor-800",
                )}
              >
                <span className="hidden sm:inline">{item.label}</span>
                <span className="sm:hidden">{item.label.split(" ").pop()}</span>
              </Link>
            ))}
          </nav>
        </div>
      </header>

      <div className="sticky top-16 sm:top-20 z-40 bg-white/80 backdrop-blur-sm border-b border-sage-200/40 shrink-0">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <nav className="flex items-center justify-between gap-4 py-2.5 text-sm">
            <div className="flex items-center gap-2">
              <Link to="/" className="text-sage-400 hover:text-harbor-600 transition-colors">
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                </svg>
              </Link>
              {breadcrumbs.map((crumb, i) => (
                <span key={crumb.path} className="flex items-center gap-2">
                  <svg className="h-4 w-4 text-sage-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                  {i === breadcrumbs.length - 1 ? (
                    <span className="font-medium text-harbor-700">{crumb.label}</span>
                  ) : (
                    <Link to={crumb.path} className="text-sage-500 hover:text-harbor-600 transition-colors">
                      {crumb.label}
                    </Link>
                  )}
                </span>
              ))}
            </div>
            
            {planId && (
              <div className="flex items-center gap-3 text-sm">
                <div className="flex items-center gap-1.5">
                  <svg className="h-4 w-4 text-sage-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                  </svg>
                  {clientName && (
                    <span className="font-medium text-harbor-700">{clientName}</span>
                  )}
                </div>
                <span className="text-sage-300">•</span>
                <button
                  onClick={() => setShowEditScenario(true)}
                  className="flex items-center gap-1.5 group/scenario rounded-lg px-2 py-1 -mx-2 -my-1 transition-colors hover:bg-sage-100"
                  title="Click to edit scenario name"
                >
                  <svg className="h-4 w-4 text-sage-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <span className="text-sage-600">{scenarioName || "Default"}</span>
                  <svg className="h-3 w-3 text-sage-400 opacity-0 group-hover/scenario:opacity-100 transition-opacity" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                  </svg>
                </button>
              </div>
            )}
          </nav>
        </div>
      </div>

      <main className="flex-1 flex flex-col mx-auto w-full max-w-7xl px-4 py-4 sm:py-6 sm:px-6 lg:px-8 min-h-0">
        <Outlet />
      </main>

      <footer className="border-t border-sage-200/60 bg-white/50 backdrop-blur-sm shrink-0">
        <div className="mx-auto max-w-7xl px-4 py-4 sm:py-6 sm:px-6 lg:px-8">
          <p className="text-center text-xs text-sage-500">
            NorthHarbor Sage &middot; Retirement Planning Assistant
          </p>
        </div>
      </footer>
    </div>
    </>
  );
}
