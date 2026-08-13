import { useEffect, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { authApi, notificationsApi } from "../api/client";
import Emblem from "./Emblem";

const PENDING_VERIFY_KEY = "ft_pending_verify_token";

const navItems = [
  { to: "/", label: "Dashboard" },
  { to: "/health", label: "Financial Health" },
  { to: "/accounts", label: "Accounts" },
  { to: "/transactions", label: "Transactions" },
  { to: "/recurring", label: "Recurring" },
  { to: "/credit-cards", label: "Credit Cards" },
  { to: "/debts", label: "Debts" },
  { to: "/investments", label: "Investments" },
  { to: "/savings-goals", label: "Savings Goals" },
  { to: "/bills", label: "Bills" },
  { to: "/statements", label: "Statements" },
  { to: "/tools", label: "Tools" },
  { to: "/budgets", label: "Budgets" },
  { to: "/categories", label: "Categories" },
  { to: "/notifications", label: "Notifications" },
  { to: "/households", label: "Households" },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [unreadCount, setUnreadCount] = useState(0);
  const [verifying, setVerifying] = useState(false);

  // Dev-mode email verification banner: after registration the Register page
  // stashes the verification token here, and this banner confirms the email
  // without leaving the app. Production would email a link instead.
  const pendingVerifyToken = sessionStorage.getItem(PENDING_VERIFY_KEY);
  const showVerifyBanner = Boolean(
    user && !user.email_verified && pendingVerifyToken && !verifying
  );

  async function handleVerify() {
    const token = sessionStorage.getItem(PENDING_VERIFY_KEY);
    if (!token) return;
    setVerifying(true);
    try {
      await authApi.verifyEmail(token);
      sessionStorage.removeItem(PENDING_VERIFY_KEY);
      // Refresh /auth/me so the sidebar chip and banner clear.
      window.location.reload();
    } catch {
      sessionStorage.removeItem(PENDING_VERIFY_KEY);
      setVerifying(false);
    }
  }

  // Lightweight polling so the unread badge stays fresh across the app; the
  // Notifications page also dispatches a change event after mutations.
  useEffect(() => {
    let cancelled = false;
    const check = () =>
      notificationsApi
        .list()
        .then((items) => {
          if (!cancelled) setUnreadCount(items.filter((n) => !n.read).length);
        })
        .catch(() => {});
    check();
    const interval = setInterval(check, 60_000);
    const onChanged = () => check();
    window.addEventListener("ft:notifications-changed", onChanged);
    return () => {
      cancelled = true;
      clearInterval(interval);
      window.removeEventListener("ft:notifications-changed", onChanged);
    };
  }, []);

  return (
    <div className="flex min-h-screen bg-slate-50">
      {showVerifyBanner && (
        <div className="fixed inset-x-0 top-0 z-50 flex items-center justify-center gap-3 bg-amber-500 px-4 py-2 text-sm text-white">
          <span>
            Verify your email to finish setting up your account (dev build — no
            email is sent).
          </span>
          <button
            onClick={handleVerify}
            className="rounded-md bg-white px-3 py-1 text-xs font-bold text-amber-600 hover:bg-amber-50"
          >
            Verify now
          </button>
        </div>
      )}
      <aside className="hidden w-56 flex-col border-r border-slate-200 bg-white p-4 md:flex">
        <div className="mb-6 flex items-center gap-2 px-2 text-lg font-bold text-slate-900">
          <Emblem />
          Finance<span className="text-emerald-600">Tracker</span>
        </div>
        <nav className="flex flex-1 flex-col gap-0.5 overflow-y-auto">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                `flex items-center justify-between rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-emerald-50 text-emerald-700"
                    : "text-slate-600 hover:bg-slate-100"
                }`
              }
            >
              <span>{item.label}</span>
              {item.to === "/notifications" && unreadCount > 0 && (
                <span className="rounded-full bg-red-500 px-1.5 py-0.5 text-[10px] font-bold leading-none text-white">
                  {unreadCount}
                </span>
              )}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-slate-200 pt-3">
          <p className="truncate px-3 text-xs text-slate-500">{user?.email}</p>
          {user && !user.email_verified && (
            <p className="mt-1.5 rounded-lg bg-amber-50 px-3 py-1.5 text-[11px] font-medium text-amber-700">
              Unverified email
            </p>
          )}
          <button
            onClick={() => {
              logout();
              navigate("/login");
            }}
            className="mt-2 w-full rounded-lg px-3 py-2 text-left text-sm font-medium text-red-600 hover:bg-red-50"
          >
            Sign out
          </button>
        </div>
      </aside>

      <main className="flex-1 p-6">
        <Outlet />
      </main>
    </div>
  );
}
