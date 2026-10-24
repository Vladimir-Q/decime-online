"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";

import type { AppLanguage } from "@/lib/app-language";
import { getCachedAppLanguage, resolveAppLanguage, ui } from "@/lib/app-language";
import type { UserPublic } from "@/types/auth";

interface AppLanguageContextValue {
  language: AppLanguage;
  setLanguage: (language: AppLanguage) => void;
  t: ReturnType<typeof ui>;
}

const AppLanguageContext = createContext<AppLanguageContextValue | null>(null);

export function AppLanguageProvider({
  user,
  children,
}: {
  user: UserPublic | null;
  children: React.ReactNode;
}) {
  const [language, setLanguageState] = useState<AppLanguage>("ru");
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const resolved = (await resolveAppLanguage(user)) ?? (await getCachedAppLanguage()) ?? "ru";
      if (!cancelled) {
        setLanguageState(resolved);
        setReady(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [user]);

  const value = useMemo(
    () => ({
      language,
      setLanguage: setLanguageState,
      t: ui(language),
    }),
    [language],
  );

  if (!ready) {
    return null;
  }

  return <AppLanguageContext.Provider value={value}>{children}</AppLanguageContext.Provider>;
}

export function useAppLanguage(): AppLanguageContextValue {
  const ctx = useContext(AppLanguageContext);
  if (!ctx) {
    return {
      language: "ru",
      setLanguage: () => undefined,
      t: ui("ru"),
    };
  }
  return ctx;
}
