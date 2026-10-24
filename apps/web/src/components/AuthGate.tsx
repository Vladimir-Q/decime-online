"use client";

import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import Link from "next/link";

import { AppFaqFooter } from "@/components/AppFaqFooter";
import { AppLanguageProvider } from "@/components/AppLanguageProvider";
import { LanguageOnboarding } from "@/components/LanguageOnboarding";
import {
  fetchCurrentUser,
  getStoredToken,
  redirectToLogin,
  resolveServerAuthEnabled,
  SESSION_EXPIRED_EVENT,
  setStoredToken,
} from "@/lib/auth";
import {
  getCachedAppLanguage,
  resolveAppLanguage,
  ui,
  type AppLanguage,
} from "@/lib/app-language";
import { isCapacitorMobileBuild } from "@/lib/capacitor-build";
import type { UserPublic } from "@/types/auth";

interface AuthGateProps {
  children: React.ReactNode;
}

export function AuthGate({ children }: AuthGateProps) {
  const pathname = usePathname();
  const [ready, setReady] = useState(false);
  const [authRequired, setAuthRequired] = useState(false);
  const [user, setUser] = useState<UserPublic | null>(null);
  const [needsLanguage, setNeedsLanguage] = useState(false);
  const [uiLanguage, setUiLanguage] = useState<AppLanguage>("ru");
  const t = ui(uiLanguage);

  useEffect(() => {
    void getCachedAppLanguage().then((cached) => {
      if (cached) {
        setUiLanguage(cached);
      }
    });
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function verify() {
      try {
        const authEnabled = await resolveServerAuthEnabled();
        if (!authEnabled) {
          await setStoredToken(null);
          const cached = await getCachedAppLanguage();
          if (!cancelled) {
            setAuthRequired(false);
            setUser(null);
            setNeedsLanguage(!cached);
            if (cached) {
              setUiLanguage(cached);
            }
            setReady(true);
          }
          return;
        }

        const token = await getStoredToken();
        if (!token) {
          if (!cancelled) {
            setAuthRequired(true);
            setUser(null);
            setNeedsLanguage(false);
            setReady(true);
          }
          return;
        }

        // One retry covers Preferences/native-HTTP races right after login navigation.
        let me: UserPublic;
        try {
          me = await fetchCurrentUser();
        } catch {
          await new Promise((resolve) => setTimeout(resolve, 250));
          if (cancelled) {
            return;
          }
          const tokenAfter = await getStoredToken();
          if (!tokenAfter) {
            throw new Error("Session cleared");
          }
          me = await fetchCurrentUser();
        }
        const language = await resolveAppLanguage(me);
        if (!cancelled) {
          setAuthRequired(false);
          setUser(me);
          setNeedsLanguage(!language);
          if (language) {
            setUiLanguage(language);
          }
          setReady(true);
        }
      } catch {
        const authEnabled = await resolveServerAuthEnabled().catch(() => false);
        if (!authEnabled) {
          await setStoredToken(null);
          const cached = await getCachedAppLanguage();
          if (!cancelled) {
            setAuthRequired(false);
            setUser(null);
            setNeedsLanguage(!cached);
            if (cached) {
              setUiLanguage(cached);
            }
            setReady(true);
          }
          return;
        }
        // If a token remains, stay on a sign-in prompt without wiping storage again
        // (authFetch may already have redirected on true 401).
        if (!cancelled) {
          setAuthRequired(true);
          setUser(null);
          setNeedsLanguage(false);
          setReady(true);
        }
      }
    }

    void verify();
    return () => {
      cancelled = true;
    };
  }, [pathname]);

  useEffect(() => {
    const onSessionExpired = () => {
      setAuthRequired(true);
      setUser(null);
    };
    window.addEventListener(SESSION_EXPIRED_EVENT, onSessionExpired);
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, onSessionExpired);
  }, []);

  useEffect(() => {
    if (ready && authRequired) {
      redirectToLogin(pathname || "/app/live/");
    }
  }, [ready, authRequired, pathname]);

  if (!ready) {
    return (
      <main className="page">
        <p className="muted">{t.checkingSession}</p>
      </main>
    );
  }

  if (authRequired) {
    return (
      <main className="page">
        <section className="card settings-section">
          <h1>{t.signInRequired}</h1>
          <p className="muted">
            {isCapacitorMobileBuild() ? t.checkingSession : t.signInRequiredLead}
          </p>
          <Link
            className="button primary"
            href={`/login/?returnTo=${encodeURIComponent(pathname || "/app/live/")}`}
          >
            {t.logIn}
          </Link>
        </section>
      </main>
    );
  }

  if (needsLanguage) {
    return (
      <LanguageOnboarding
        onChosen={(language: AppLanguage) => {
          setUser((current) => (current ? { ...current, app_language: language } : current));
          setUiLanguage(language);
          setNeedsLanguage(false);
        }}
      />
    );
  }

  return (
    <AppLanguageProvider user={user}>
      <div className="app-shell">
        {user?.role === "admin" && !isCapacitorMobileBuild() ? (
          <p className="auth-admin-hint muted">
            {t.adminHint} {user.email} · <Link href="/app/admin/users/">{t.navAdminUsers}</Link>
            {" · "}
            <Link href="/app/admin/ai/">{t.navAdminAi}</Link>
            {" · "}
            <Link href="/app/admin/usage/">{t.navAdminUsage}</Link>
          </p>
        ) : null}
        {children}
        <AppFaqFooter />
      </div>
    </AppLanguageProvider>
  );
}
