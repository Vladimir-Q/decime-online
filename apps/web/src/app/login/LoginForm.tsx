"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

import { AppNavLink } from "@/components/AppNavLink";
import { fetchAuthConfig, getStoredToken, login, register } from "@/lib/auth";
import {
  getCachedAppLanguage,
  ui,
  type AppLanguage,
} from "@/lib/app-language";
import { isCapacitorMobileBuild } from "@/lib/capacitor-build";
import { navigateInApp } from "@/lib/capacitor-navigation";

export function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const returnTo = searchParams.get("returnTo") || "/app/live/";

  const [language, setLanguage] = useState<AppLanguage>("ru");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [allowRegistration, setAllowRegistration] = useState(false);
  const [mode, setMode] = useState<"login" | "register">("login");
  const [authDisabled, setAuthDisabled] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const t = ui(language);

  function goAfterAuth(target: string) {
    if (isCapacitorMobileBuild()) {
      navigateInApp(target);
      return;
    }
    router.replace(target);
  }

  useEffect(() => {
    void getCachedAppLanguage().then((cached) => {
      if (cached) {
        setLanguage(cached);
      }
    });
  }, []);

  useEffect(() => {
    void (async () => {
      try {
        const config = await fetchAuthConfig(true);
        setAllowRegistration(config.allow_registration);
        if (!config.auth_enabled) {
          setAuthDisabled(true);
          goAfterAuth(returnTo);
        }
      } catch {
        try {
          const { getApiBaseUrl, joinApiPath } = await import("@/lib/api-config");
          const baseUrl = await getApiBaseUrl();
          const response = await fetch(joinApiPath(baseUrl, "/health"), { cache: "no-store" });
          if (response.ok) {
            const health = (await response.json()) as { auth_enabled?: string | boolean };
            const off =
              health.auth_enabled === false ||
              health.auth_enabled === "false" ||
              health.auth_enabled === undefined;
            if (off) {
              setAuthDisabled(true);
              goAfterAuth(returnTo);
            }
          }
        } catch {
          // API unreachable — show form
        }
      }
    })();
  }, [router, returnTo]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const normalizedEmail = email.trim();
      if (mode === "register") {
        await register({
          email: normalizedEmail,
          password,
          display_name: displayName || undefined,
        });
      } else {
        await login({ email: normalizedEmail, password });
      }
      const token = await getStoredToken();
      if (!token) {
        throw new Error(
          language === "ru"
            ? "Вход выполнен, но сессия не сохранилась. Попробуйте ещё раз."
            : "Signed in, but the session was not saved. Please try again.",
        );
      }
      goAfterAuth(returnTo);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="page">
      <section className="hero">
        <p className="eyebrow">Decime UY</p>
        <h1>{mode === "login" ? t.loginSignIn : t.loginCreateAccount}</h1>
      </section>

      <section className="card settings-section">
        <form className="compose-form" onSubmit={handleSubmit}>
          <label className="field-label" htmlFor="login-email">
            {t.loginEmail}
          </label>
          <input
            id="login-email"
            className="input"
            type="email"
            autoComplete="username"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />

          <label className="field-label" htmlFor="login-password">
            {t.loginPassword}
          </label>
          <input
            id="login-password"
            className="input"
            type="password"
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            minLength={8}
            required
          />

          {mode === "register" ? (
            <>
              <label className="field-label" htmlFor="login-display-name">
                {t.loginName}
              </label>
              <input
                id="login-display-name"
                className="input"
                value={displayName}
                onChange={(event) => setDisplayName(event.target.value)}
              />
            </>
          ) : null}

          {error ? <p className="error">{error}</p> : null}

          <button type="submit" className="button primary" disabled={busy}>
            {busy ? t.loginBusy : mode === "login" ? t.loginSubmit : t.loginRegister}
          </button>
        </form>

        {allowRegistration ? (
          <p className="muted">
            {mode === "login" ? (
              <button type="button" className="link-button" onClick={() => setMode("register")}>
                {t.loginNeedAccount}
              </button>
            ) : (
              <button type="button" className="link-button" onClick={() => setMode("login")}>
                {t.loginHaveAccount}
              </button>
            )}
          </p>
        ) : null}

        <p className="muted">
          <Link href="/app/live/">{t.loginOpenApp}</Link>
        </p>
        {authDisabled ? (
          <p className="muted">{t.checkingSession}</p>
        ) : null}
      </section>
      <p className="app-faq-footer">
        <AppNavLink href="/faq/">{t.footerFaq}</AppNavLink>
      </p>
    </main>
  );
}
