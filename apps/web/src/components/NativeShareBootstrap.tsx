"use client";

import { useEffect } from "react";

import { getApiBaseUrl, autoDiscoverApiUrl, migrateStaleApiUrl, probeDecimeHealth, resetApiBaseUrlCache, setApiBaseUrl } from "@/lib/api-config";
import { isCapacitorMobileBuild } from "@/lib/capacitor-build";
import { navigateInApp } from "@/lib/capacitor-navigation";
import {
  installCapacitorNavigationFix,
  isNativePlatform,
  routeToQuickReplyIfPendingShare,
} from "@/lib/native-share";

const POLL_ATTEMPTS = 40;
const POLL_INTERVAL_MS = 150;

export function NativeShareBootstrap() {
  useEffect(() => {
    if (!isNativePlatform()) {
      return;
    }

    const removeNavigationFix = installCapacitorNavigationFix();
    (window as Window & { __decimeResetApiCache?: () => void }).__decimeResetApiCache = () => {
      resetApiBaseUrlCache();
    };
    void (async () => {
      await migrateStaleApiUrl();
      const { clearStaleSharePrefsIfNotForced } = await import("@/lib/native-share");
      await clearStaleSharePrefsIfNotForced();
      const url = await getApiBaseUrl();
      if (!url) {
        await autoDiscoverApiUrl();
        return;
      }
      try {
        await probeDecimeHealth(url);
      } catch {
        await autoDiscoverApiUrl();
      }
    })();

    const onApiUrlInjected = () => {
      resetApiBaseUrlCache();
      void getApiBaseUrl();
    };
    window.addEventListener("decime-api-url", onApiUrlInjected);

    const onConnE2E = (event: Event) => {
      if (!isCapacitorMobileBuild()) {
        return;
      }
      const detail = (event as CustomEvent<{ action?: string; payload?: string | null }>).detail;
      if (detail?.action === "nav" && detail.payload) {
        navigateInApp(detail.payload);
        window.setTimeout(() => {
          console.log(
            `DECIME_NAV_E2E|${JSON.stringify({
              requested: detail.payload,
              pathname: window.location.pathname,
            })}`,
          );
        }, 500);
        return;
      }
      if (!detail?.action?.startsWith("conn-")) {
        return;
      }
      void (async () => {
        if (detail.action === "conn-save" && detail.payload) {
          const normalized = await setApiBaseUrl(detail.payload);
          console.log(
            `DECIME_CONN_E2E|${JSON.stringify({ savedUrl: normalized, draftUrl: normalized, healthOk: null, healthApp: null, error: null })}`,
          );
          return;
        }
        if (detail.action === "conn-test") {
          const url = (detail.payload || (await getApiBaseUrl()) || "").trim();
          try {
            const health = await probeDecimeHealth(url);
            console.log(
              `DECIME_CONN_E2E|${JSON.stringify({
                savedUrl: url,
                draftUrl: url,
                healthOk: true,
                healthApp: health.app,
                error: null,
              })}`,
            );
          } catch (testError) {
            console.log(
              `DECIME_CONN_E2E|${JSON.stringify({
                savedUrl: url,
                draftUrl: url,
                healthOk: false,
                error: testError instanceof Error ? testError.message : "probe failed",
              })}`,
            );
          }
        }
      })();
    };
    window.addEventListener("decime-e2e-action", onConnE2E);

    let cancelled = false;

    const pollPendingShare = (attempt = 0) => {
      if (cancelled) {
        return;
      }

      void routeToQuickReplyIfPendingShare().then((routed) => {
        if (cancelled || routed) {
          return;
        }
        if (attempt < POLL_ATTEMPTS) {
          window.setTimeout(() => pollPendingShare(attempt + 1), POLL_INTERVAL_MS);
        }
      });
    };

    pollPendingShare();

    const onShareUpdated = () => {
      pollPendingShare();
    };
    window.addEventListener("decime-share-updated", onShareUpdated);

    let removeListener: (() => void) | undefined;

    void (async () => {
      const { App } = await import("@capacitor/app");
      const handle = await App.addListener("appStateChange", ({ isActive }) => {
        if (isActive) {
          pollPendingShare();
        }
      });
      removeListener = () => {
        void handle.remove();
      };
    })();

    return () => {
      cancelled = true;
      window.removeEventListener("decime-api-url", onApiUrlInjected);
      window.removeEventListener("decime-e2e-action", onConnE2E);
      window.removeEventListener("decime-share-updated", onShareUpdated);
      removeNavigationFix();
      removeListener?.();
    };
  }, []);

  return null;
}
