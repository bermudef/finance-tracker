import { useCallback, useEffect, useMemo, useState } from "react";
import {
  householdsApi,
  type Household,
  type HouseholdInvite,
  type HouseholdMember,
  type PendingHouseholdInvite,
} from "../api/client";
import { useAuth } from "../context/AuthContext";
import { Badge, Card } from "../components/ui";

const ROLE_TONES: Record<string, string> = {
  owner: "amber",
  admin: "blue",
  member: "slate",
};

function formatExpiry(iso: string): string {
  const d = new Date(iso.endsWith("Z") ? iso : `${iso}Z`);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

export default function HouseholdsPage() {
  const { user } = useAuth();
  const [households, setHouseholds] = useState<Household[]>([]);
  const [pending, setPending] = useState<PendingHouseholdInvite[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [members, setMembers] = useState<HouseholdMember[]>([]);
  const [invites, setInvites] = useState<HouseholdInvite[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // ---- form state ----
  const [newName, setNewName] = useState("");
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("member");

  const loadAll = useCallback(async () => {
    try {
      const [hs, pd] = await Promise.all([householdsApi.list(), householdsApi.pending()]);
      setHouseholds(hs);
      setPending(pd);
      setSelectedId((current) =>
        current === null && hs.length > 0 ? hs[0].id : current
      );
    } catch (err) {
      setError((err as Error).message);
    }
  }, []);

  useEffect(() => {
    void loadAll();
  }, [loadAll]);

  const loadDetail = useCallback(
    async (householdId: number) => {
      setError(null);
      try {
        const ms = await householdsApi.members(householdId);
        setMembers(ms);
        // Only owners/admins may list invites — don't issue a request that
        // would 403 for plain members.
        const myRole = ms.find((m) => m.user_id === user?.id)?.role;
        setInvites(
          myRole === "owner" || myRole === "admin"
            ? await householdsApi.invites(householdId)
            : []
        );
      } catch (err) {
        setError((err as Error).message);
      }
    },
    [user]
  );

  useEffect(() => {
    if (selectedId !== null) void loadDetail(selectedId);
  }, [selectedId, loadDetail]);

  const selected = useMemo(
    () => households.find((h) => h.id === selectedId) ?? null,
    [households, selectedId]
  );

  const myRole = useMemo(
    () => members.find((m) => m.user_id === user?.id)?.role ?? null,
    [members, user]
  );
  const canManage = myRole === "owner" || myRole === "admin";

  const createHousehold = async () => {
    if (!newName.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const created = await householdsApi.create(newName.trim());
      setNewName("");
      await loadAll();
      setSelectedId(created.id);
      await loadDetail(created.id);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const sendInvite = async () => {
    if (!selected || !inviteEmail.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await householdsApi.createInvite(selected.id, inviteEmail.trim(), inviteRole);
      setInviteEmail("");
      await loadDetail(selected.id);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const cancelInvite = async (inviteId: number) => {
    if (!selected) return;
    try {
      await householdsApi.cancelInvite(selected.id, inviteId);
      await loadDetail(selected.id);
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const acceptInvite = async (invite: PendingHouseholdInvite) => {
    setBusy(true);
    setError(null);
    try {
      const result = await householdsApi.accept(invite.token);
      await loadAll();
      setSelectedId(result.household_id);
      await loadDetail(result.household_id);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold text-slate-900">Households</h1>
        <p className="text-sm text-slate-500">
          Shared finances for family and partners — invite people by email
        </p>
      </header>

      {error && (
        <p className="rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-700">{error}</p>
      )}

      {pending.length > 0 && (
        <section>
          <h2 className="mb-2 text-sm font-semibold text-slate-700">
            Pending invitations ({pending.length})
          </h2>
          <div className="space-y-2">
            {pending.map((invite) => {
              const expired = new Date(invite.expires_at) < new Date();
              return (
                <Card key={invite.id} className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-slate-900">
                      {invite.household_name}
                      <Badge tone={ROLE_TONES[invite.role] ?? "slate"}>{invite.role}</Badge>
                    </p>
                    <p className="mt-0.5 text-xs text-slate-500">
                      Invited as {invite.role} · expires {formatExpiry(invite.expires_at)}
                      {expired && " (expired)"}
                    </p>
                  </div>
                  <button
                    onClick={() => acceptInvite(invite)}
                    disabled={busy || expired}
                    className="rounded-lg bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
                  >
                    Accept invite
                  </button>
                </Card>
              );
            })}
          </div>
        </section>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
        {/* Left: my households + create */}
        <section className="space-y-3 lg:col-span-2">
          <Card>
            <h2 className="text-sm font-semibold text-slate-700">Create household</h2>
            <div className="mt-2 flex gap-2">
              <input
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && createHousehold()}
                placeholder="e.g. The Smith Family"
                className="flex-1 rounded-lg border border-slate-300 px-3 py-1.5 text-sm focus:border-emerald-500 focus:outline-none"
              />
              <button
                onClick={createHousehold}
                disabled={busy || !newName.trim()}
                className="rounded-lg bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
              >
                Create
              </button>
            </div>
          </Card>

          <h2 className="text-sm font-semibold text-slate-700">My households</h2>
          {households.length === 0 ? (
            <p className="rounded-xl border border-dashed border-slate-300 bg-white p-4 text-sm text-slate-500">
              You don't belong to a household yet. Create one above to get started.
            </p>
          ) : (
            <ul className="space-y-2">
              {households.map((h) => (
                <li key={h.id}>
                  <button
                    onClick={() => setSelectedId(h.id)}
                    className={`w-full rounded-xl border p-4 text-left transition-colors ${
                      h.id === selectedId
                        ? "border-emerald-500 bg-emerald-50/60"
                        : "border-slate-200 bg-white hover:border-slate-300"
                    }`}
                  >
                    <p className="text-sm font-semibold text-slate-900">{h.name}</p>
                    <p className="mt-0.5 text-xs text-slate-500">
                      Created {formatExpiry(h.created_at)}
                    </p>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>

        {/* Right: selected household detail */}
        <section className="space-y-4 lg:col-span-3">
          {selected ? (
            <>
              <Card>
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-base font-semibold text-slate-900">{selected.name}</h2>
                    <p className="text-xs text-slate-500">
                      You are a{" "}
                      <Badge tone={ROLE_TONES[myRole ?? "member"]}>{myRole ?? "member"}</Badge>
                    </p>
                  </div>
                  <span className="text-xs text-slate-400">
                    {members.length} member{members.length === 1 ? "" : "s"}
                  </span>
                </div>

                <h3 className="mt-4 text-sm font-semibold text-slate-700">Members</h3>
                <ul className="mt-2 divide-y divide-slate-100">
                  {members.map((m) => (
                    <li key={m.id} className="flex items-center justify-between py-2 text-sm">
                      <span className="text-slate-800">
                        {m.email}
                        {m.user_id === user?.id && (
                          <span className="ml-2 text-xs text-slate-400">(you)</span>
                        )}
                      </span>
                      <Badge tone={ROLE_TONES[m.role] ?? "slate"}>{m.role}</Badge>
                    </li>
                  ))}
                </ul>
              </Card>

              {canManage && (
                <Card>
                  <h3 className="text-sm font-semibold text-slate-700">Invite someone</h3>
                  <div className="mt-2 flex flex-wrap gap-2">
                    <input
                      type="email"
                      value={inviteEmail}
                      onChange={(e) => setInviteEmail(e.target.value)}
                      onKeyDown={(e) => e.key === "Enter" && sendInvite()}
                      placeholder="partner@example.com"
                      className="min-w-52 flex-1 rounded-lg border border-slate-300 px-3 py-1.5 text-sm focus:border-emerald-500 focus:outline-none"
                    />
                    <select
                      value={inviteRole}
                      onChange={(e) => setInviteRole(e.target.value)}
                      className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm focus:border-emerald-500 focus:outline-none"
                    >
                      <option value="member">Member</option>
                      <option value="admin">Admin</option>
                    </select>
                    <button
                      onClick={sendInvite}
                      disabled={busy || !inviteEmail.trim()}
                      className="rounded-lg bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
                    >
                      Send invite
                    </button>
                  </div>

                  {invites.length > 0 && (
                    <>
                      <h3 className="mt-4 text-sm font-semibold text-slate-700">Sent invites</h3>
                      <ul className="mt-2 divide-y divide-slate-100">
                        {invites.map((invite) => {
                          const expired = new Date(invite.expires_at) < new Date();
                          return (
                            <li key={invite.id} className="flex items-center justify-between py-2 text-sm">
                              <div>
                                <span className="text-slate-800">{invite.email}</span>
                                <Badge tone={ROLE_TONES[invite.role] ?? "slate"}>
                                  {invite.role}
                                </Badge>
                                {invite.accepted_at ? (
                                  <Badge tone="green">accepted</Badge>
                                ) : expired ? (
                                  <Badge tone="red">expired</Badge>
                                ) : (
                                  <Badge tone="blue">pending</Badge>
                                )}
                              </div>
                              {!invite.accepted_at && (
                                <button
                                  onClick={() => cancelInvite(invite.id)}
                                  className="rounded-lg px-2 py-1 text-xs font-medium text-slate-400 hover:bg-red-50 hover:text-red-600"
                                >
                                  Cancel
                                </button>
                              )}
                            </li>
                          );
                        })}
                      </ul>
                    </>
                  )}
                </Card>
              )}
            </>
          ) : (
            <p className="rounded-xl border border-dashed border-slate-300 bg-white p-6 text-center text-sm text-slate-500">
              Select a household to see its members and invites.
            </p>
          )}
        </section>
      </div>
    </div>
  );
}
