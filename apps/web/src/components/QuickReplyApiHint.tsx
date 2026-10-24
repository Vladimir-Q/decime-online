"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { useAppLanguage } from "@/components/AppLanguageProvider";
import {
  getApiBaseUrl,
  isRemoteProductionApi,
  isStaleExampleApiUrl,
  needsLanSetup,
  probeDecimeHealth,
} from "@/lib/api-config";
import { isCapacitorMobileBuild, isProductionMobileBuild } from "@/lib/capacitor-build";
import { isNativePlatform } from "@/lib/native-share";

interface QuickReplyApiHintProps {
  error: string | null;
}

export function QuickReplyApiHint({ error }: QuickReplyApiHintProps) {
  const { t, language } = useAppLanguage();
  const mobileShell = isCapacitorMobileBuild() || isNativePlatform();
  const productionMobile = isProductionMobileBuild();
  const [unreachable, setUnreachable] = useState(false);
  const [savedUrl, setSavedUrl] = useState("");

  useEffect(() => {
    if (!mobileShell) {
      return;
    }

    async function refreshHint() {
      const url = await getApiBaseUrl();
      setSavedUrl(url);
      const needsSetup = needsLanSetup(url) || isStaleExampleApiUrl(url);
      if (!url || needsSetup) {
        setUnreachable(true);
        return;
      }
      try {
        await probeDecimeHealth(url);
        setUnreachable(false);
      } catch {
        setUnreachable(true);
      }
    }

    void refreshHint();
    const onApiUrl = () => {
      void refreshHint();
    };
    window.addEventListener("decime-api-url", onApiUrl);
    return () => window.removeEventListener("decime-api-url", onApiUrl);
  }, [mobileShell]);

  if (!mobileShell) {
    return null;
  }

  const apiError =
    error &&
    (error.includes("API") ||
      error.includes("fetch") ||
      error.includes("Cannot reach") ||
      error.includes("Network") ||
      error.includes("connection") ||
      error.includes("Session expired"));

  if (!apiError && !unreachable) {
    return null;
  }

  const productionUrl = isRemoteProductionApi(savedUrl);
  const networkHint =
    language === "ru"
      ? productionUrl || productionMobile
        ? "Проверьте интернет и войдите в аккаунт."
        : "Проверьте Wi‑Fi и доступность сервера."
      : productionUrl || productionMobile
        ? "Check internet connection and sign in."
        : "Check Wi‑Fi and server availability.";

  return (
    <p className="quick-reply-api-hint">
      {unreachable && !apiError ? (
        <>
          {language === "ru" ? "Нет связи с сервером. " : "Cannot reach the server. "}
          {networkHint}{" "}
        </>
      ) : null}
      {apiError && error?.includes("Session expired") ? (
        <>
          {language === "ru" ? "Сессия истекла. " : "Session expired. "}
          <Link href="/login/">{t.logIn}</Link>
        </>
      ) : apiError ? (
        <>{networkHint}</>
      ) : null}
    </p>
  );
}
