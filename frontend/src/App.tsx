import { lazy, Suspense } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import Layout from "./components/Layout";

// Route-level code splitting: each page is its own chunk, loaded on demand.
// Recharts (the heaviest dependency) only loads when the dashboard mounts.
const LoginPage = lazy(() => import("./pages/Login"));
const RegisterPage = lazy(() => import("./pages/Register"));
const ForgotPasswordPage = lazy(() => import("./pages/ForgotPassword"));
const ResetPasswordPage = lazy(() => import("./pages/ResetPassword"));
const DashboardPage = lazy(() => import("./pages/Dashboard"));
const TransactionsPage = lazy(() => import("./pages/Transactions"));
const AccountsPage = lazy(() => import("./pages/Accounts"));
const CategoriesPage = lazy(() => import("./pages/Categories"));
const BudgetsPage = lazy(() => import("./pages/Budgets"));
const CreditCardsPage = lazy(() => import("./pages/CreditCards"));
const DebtsPage = lazy(() => import("./pages/Debts"));
const InvestmentsPage = lazy(() => import("./pages/Investments"));
const SavingsGoalsPage = lazy(() => import("./pages/SavingsGoals"));
const BillsPage = lazy(() => import("./pages/Bills"));
const StatementsPage = lazy(() => import("./pages/Statements"));
const ToolsPage = lazy(() => import("./pages/Tools"));

function PageFallback() {
  return <p className="p-8 text-sm text-slate-500">Loading…</p>;
}

function Protected({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <PageFallback />;
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function PublicOnly({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <PageFallback />;
  if (user) return <Navigate to="/" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Suspense fallback={<PageFallback />}>
          <Routes>
            <Route
              path="/login"
              element={
                <PublicOnly>
                  <LoginPage />
                </PublicOnly>
              }
            />
            <Route
              path="/register"
              element={
                <PublicOnly>
                  <RegisterPage />
                </PublicOnly>
              }
            />
            <Route
              path="/forgot-password"
              element={
                <PublicOnly>
                  <ForgotPasswordPage />
                </PublicOnly>
              }
            />
            <Route
              path="/reset-password"
              element={
                <PublicOnly>
                  <ResetPasswordPage />
                </PublicOnly>
              }
            />
            <Route
              path="/"
              element={
                <Protected>
                  <Layout />
                </Protected>
              }
            >
              <Route index element={<DashboardPage />} />
              <Route path="transactions" element={<TransactionsPage />} />
              <Route path="budgets" element={<BudgetsPage />} />
              <Route path="accounts" element={<AccountsPage />} />
              <Route path="categories" element={<CategoriesPage />} />
              <Route path="credit-cards" element={<CreditCardsPage />} />
              <Route path="debts" element={<DebtsPage />} />
              <Route path="investments" element={<InvestmentsPage />} />
              <Route path="savings-goals" element={<SavingsGoalsPage />} />
              <Route path="bills" element={<BillsPage />} />
              <Route path="statements" element={<StatementsPage />} />
              <Route path="tools" element={<ToolsPage />} />
            </Route>
          </Routes>
        </Suspense>
      </AuthProvider>
    </BrowserRouter>
  );
}
