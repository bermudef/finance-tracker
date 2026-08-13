import { useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import Emblem from "../components/Emblem";

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") ?? "";

  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (password !== confirm) {
      setError("Passwords do not match");
      return;
    }
    if (!token) {
      setError("Missing reset token. Use the link from your email.");
      return;
    }
    setSubmitting(true);
    setError(null);
    setMessage(null);
    try {
      const resp = await api.post<{ message: string }>("/auth/reset-password", {
        token,
        new_password: password,
      });
      setMessage(resp.message);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Request failed");
    } finally {
      setSubmitting(false);
    }
  }

  const inputClass =
    "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500";

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 p-4">
      <div className="w-full max-w-sm">
        <h1 className="mb-6 flex flex-col items-center gap-2 text-2xl font-bold text-slate-900">
          <Emblem className="h-10 w-10" />
          Finance<span className="text-emerald-600">Tracker</span>
        </h1>
        <form onSubmit={handleSubmit} className="space-y-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-900">Choose a new password</h2>
          {message && (
            <div className="space-y-2 rounded-lg bg-emerald-50 p-3">
              <p className="text-sm text-emerald-700">{message}</p>
              <Link
                to="/login"
                className="block text-sm font-medium text-emerald-600 hover:underline"
              >
                Sign in with your new password →
              </Link>
            </div>
          )}
          {error && (
            <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
          )}
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="password">
              New password (min 8 characters)
            </label>
            <input
              id="password"
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className={inputClass}
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="confirm">
              Confirm new password
            </label>
            <input
              id="confirm"
              type="password"
              required
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              className={inputClass}
            />
          </div>
          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-lg bg-emerald-600 py-2 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-50"
          >
            {submitting ? "Resetting…" : "Reset password"}
          </button>
          <p className="text-center text-sm text-slate-500">
            <Link to="/login" className="font-medium text-emerald-600 hover:underline">
              Back to sign in
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}
