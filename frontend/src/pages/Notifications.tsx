import { useCallback, useEffect, useState } from "react";
import { notificationsApi, type NotificationItem } from "../api/client";
import { Badge, Card } from "../components/ui";

const TYPE_TONES: Record<string, string> = {
  bill_reminder: "blue",
  budget_alert: "amber",
  savings_milestone: "green",
  general: "slate",
};

function relativeTime(iso: string): string {
  // Backend timestamps are naive UTC; treat them as UTC so the offset is right.
  const parsed = new Date(iso.endsWith("Z") ? iso : `${iso}Z`);
  const seconds = Math.floor((Date.now() - parsed.getTime()) / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  return parsed.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

const notifyChanged = () => window.dispatchEvent(new Event("ft:notifications-changed"));

export default function NotificationsPage() {
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(() => {
    setLoading(true);
    notificationsApi
      .list()
      .then(setItems)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(refresh, [refresh]);

  const generate = async () => {
    setBusy(true);
    setError(null);
    try {
      const created = await notificationsApi.generate();
      if (created.length === 0) setError("Nothing new — bills and budgets are all clear.");
      refresh();
      notifyChanged();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const markAllRead = async () => {
    setBusy(true);
    try {
      await notificationsApi.markAllRead();
      refresh();
      notifyChanged();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const markRead = async (id: number) => {
    try {
      await notificationsApi.markRead(id);
      setItems((prev) => prev.map((n) => (n.id === id ? { ...n, read: true } : n)));
      notifyChanged();
    } catch {
      /* keep the row as-is; refresh will reconcile */
    }
  };

  const remove = async (id: number) => {
    try {
      await notificationsApi.remove(id);
      setItems((prev) => prev.filter((n) => n.id !== id));
      notifyChanged();
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const unread = items.filter((n) => !n.read).length;

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Notifications</h1>
          <p className="text-sm text-slate-500">
            Bill reminders and budget alerts generated from your live data
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={markAllRead}
            disabled={busy || unread === 0}
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
          >
            Mark all read
          </button>
          <button
            onClick={generate}
            disabled={busy}
            className="rounded-lg bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
          >
            {busy ? "Checking…" : "Generate reminders"}
          </button>
        </div>
      </header>

      {error && (
        <p className="rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-700">{error}</p>
      )}

      {loading ? (
        <p className="text-sm text-slate-500">Loading notifications…</p>
      ) : items.length === 0 ? (
        <Card className="text-center">
          <p className="text-sm font-medium text-slate-700">No notifications yet</p>
          <p className="mt-1 text-xs text-slate-500">
            Click "Generate reminders" to check for bills due within a week and budgets that are
            over or at risk.
          </p>
        </Card>
      ) : (
        <ul className="space-y-2">
          {items.map((n) => (
            <li
              key={n.id}
              className={`flex items-start justify-between gap-3 rounded-xl border bg-white p-4 shadow-sm transition-colors ${
                n.read ? "border-slate-200" : "border-emerald-300 bg-emerald-50/50"
              }`}
            >
              <button
                onClick={() => !n.read && markRead(n.id)}
                className="flex-1 text-left"
                aria-label={n.read ? undefined : `Mark ${n.title} as read`}
              >
                <div className="flex items-center gap-2">
                  <Badge tone={TYPE_TONES[n.type] ?? "slate"}>
                    {n.type.replace("_", " ")}
                  </Badge>
                  {!n.read && <span className="h-2 w-2 rounded-full bg-emerald-500" />}
                  <span className="text-xs text-slate-400">{relativeTime(n.created_at)}</span>
                </div>
                <p className="mt-1 text-sm font-semibold text-slate-900">{n.title}</p>
                <p className="mt-0.5 text-sm text-slate-600">{n.message}</p>
              </button>
              <button
                onClick={() => remove(n.id)}
                className="rounded-lg px-2 py-1 text-xs font-medium text-slate-400 hover:bg-red-50 hover:text-red-600"
                aria-label="Delete notification"
              >
                Delete
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
