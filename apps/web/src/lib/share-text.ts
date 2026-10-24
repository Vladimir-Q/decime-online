import { getApiBaseUrl } from "@/lib/api-config";
import { fetchAuthConfig, getStoredToken } from "@/lib/auth";
import { isCapacitorMobileBuild } from "@/lib/capacitor-build";
import { clampTranslationText } from "@/lib/translation-limits";

const INVISIBLE_CHARS = /[\u200B-\u200D\uFEFF\u202A-\u202E]/g;

/** Normalize text received from WhatsApp / Android share intents. */
export function sanitizeSharedText(raw: string): string {
  return clampTranslationText(
    raw
      .replace(INVISIBLE_CHARS, "")
      .replace(/\r\n/g, "\n")
      .replace(/[ \t]+\n/g, "\n")
      .trim(),
  );
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

/**
 * Share cold-start fires translate while native API URL + JWT may still be loading.
 * Wait briefly so the first understand-text call is authenticated and routed correctly.
 */
export async function waitForShareTranslateReady(maxMs = 10_000): Promise<void> {
  if (!isCapacitorMobileBuild()) {
    return;
  }

  const deadline = Date.now() + maxMs;
  let authEnabled = true;

  while (Date.now() < deadline) {
    const baseUrl = await getApiBaseUrl();
    if (!baseUrl) {
      await delay(150);
      continue;
    }

    try {
      const config = await fetchAuthConfig();
      authEnabled = config.auth_enabled;
    } catch {
      await delay(150);
      continue;
    }

    if (!authEnabled) {
      return;
    }

    const token = await getStoredToken();
    if (token) {
      return;
    }

    await delay(150);
  }
}

export function isRetryableTranslateError(message: string): boolean {
  const lower = message.toLowerCase();
  return (
    lower.includes("502") ||
    lower.includes("503") ||
    lower.includes("504") ||
    lower.includes("timeout") ||
    lower.includes("temporarily unavailable") ||
    lower.includes("rate limit")
  );
}
