import { Link, Outlet, useLocation } from "react-router-dom";
import { cn } from "../../lib/utils";
import logoSingleLine from "../../../../logo-single-line.jpeg";

const NAV_ITEMS = [
  { path: "/plans", label: "Plans" },
  { path: "/interview", label: "New Interview" },
];

export default function Layout() {
  const location = useLocation();

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
          <Link to="/" className="flex items-center gap-2">
            <img
              src={logoSingleLine}
              alt="NorthHarbor Sage"
              className="h-8 w-auto"
            />
          </Link>

          <nav className="flex gap-1">
            {NAV_ITEMS.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                className={cn(
                  "rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                  location.pathname.startsWith(item.path)
                    ? "bg-harbor-50 text-harbor-700"
                    : "text-gray-600 hover:bg-gray-100 hover:text-gray-900",
                )}
              >
                {item.label}
              </Link>
            ))}
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <Outlet />
      </main>
    </div>
  );
}
