"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

import { AppNav } from "@/components/AppNav";
import { createUser, fetchCurrentUser, listUsers, logout, updateUser } from "@/lib/auth";
import { isCapacitorMobileBuild } from "@/lib/capacitor-build";
import { navigateInApp } from "@/lib/capacitor-navigation";
import type { UserPublic, UserRole } from "@/types/auth";

export function UsersAdminPage() {
  const [users, setUsers] = useState<UserPublic[]>([]);
  const [me, setMe] = useState<UserPublic | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [blockedOnMobile, setBlockedOnMobile] = useState(false);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [role, setRole] = useState<UserRole>("user");

  async function reload() {
    const current = await fetchCurrentUser();
    if (current.role !== "admin") {
      throw new Error("Admin access required");
    }
    setMe(current);
    setUsers(await listUsers());
  }

  useEffect(() => {
    if (isCapacitorMobileBuild()) {
      setBlockedOnMobile(true);
      navigateInApp("/app/live/");
      return;
    }
    void reload().catch((loadError) => {
      setError(loadError instanceof Error ? loadError.message : "Could not load users");
    });
  }, []);

  if (blockedOnMobile) {
    return (
      <main className="page">
        <p className="muted">Admin console is web-only. Redirecting…</p>
      </main>
    );
  }

  async function handleCreate(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await createUser({
        email,
        password,
        display_name: displayName || undefined,
        role,
      });
      setEmail("");
      setPassword("");
      setDisplayName("");
      setRole("user");
      await reload();
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : "Create failed");
    } finally {
      setBusy(false);
    }
  }

  async function toggleActive(user: UserPublic) {
    setBusy(true);
    setError(null);
    try {
      await updateUser(user.id, { is_active: !user.is_active });
      await reload();
    } catch (updateError) {
      setError(updateError instanceof Error ? updateError.message : "Update failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="page">
      <AppNav isAdmin />
      <section className="hero">
        <p className="eyebrow">Admin</p>
        <h1>Users</h1>
        <p className="lead">
          Manage accounts for the VM deployment.{" "}
          <Link href="/app/admin/ai/">AI power</Link>
        </p>
      </section>

      {error ? <p className="error">{error}</p> : null}

      <section className="card settings-section">
        <h2>Create user</h2>
        <form className="compose-form" onSubmit={handleCreate}>
          <label className="field-label" htmlFor="user-email">
            Email
          </label>
          <input
            id="user-email"
            className="input"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />
          <label className="field-label" htmlFor="user-password">
            Password
          </label>
          <input
            id="user-password"
            className="input"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            minLength={8}
            required
          />
          <label className="field-label" htmlFor="user-display-name">
            Display name
          </label>
          <input
            id="user-display-name"
            className="input"
            value={displayName}
            onChange={(event) => setDisplayName(event.target.value)}
          />
          <label className="field-label" htmlFor="user-role">
            Role
          </label>
          <select
            id="user-role"
            className="select"
            value={role}
            onChange={(event) => setRole(event.target.value as UserRole)}
          >
            <option value="user">user</option>
            <option value="admin">admin</option>
          </select>
          <button type="submit" className="button primary" disabled={busy}>
            {busy ? "..." : "Create user"}
          </button>
        </form>
      </section>

      <section className="card settings-section">
        <h2>All users</h2>
        <ul className="scan-results">
          {users.map((user) => (
            <li key={user.id}>
              <div className="user-admin-row">
                <div>
                  <strong>{user.email}</strong>
                  <span className="muted">
                    {" "}
                    · {user.role} · {user.is_active ? "active" : "disabled"}
                  </span>
                </div>
                {me?.id !== user.id ? (
                  <button
                    type="button"
                    className="button secondary small"
                    disabled={busy}
                    onClick={() => void toggleActive(user)}
                  >
                    {user.is_active ? "Disable" : "Enable"}
                  </button>
                ) : (
                  <span className="muted">you</span>
                )}
              </div>
            </li>
          ))}
        </ul>
        <button
          type="button"
          className="button secondary"
          onClick={() => {
            void logout().then(() => {
              window.location.href = "/login/";
            });
          }}
        >
          Log out
        </button>
      </section>
    </main>
  );
}
