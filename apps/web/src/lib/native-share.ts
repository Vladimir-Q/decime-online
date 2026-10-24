import { Capacitor } from "@capacitor/core";

import {
  installCapacitorAnchorHrefObserver,
  navigateInApp,
  normalizeAppPath,
  patchInternalAnchorHrefs,
} from "@/lib/capacitor-navigation";

const FORCE_QUICK_REPLY_KEY = "decime_force_quick_reply";
const PENDING_SHARE_TEXT_KEY = "decime_pending_share_text";
const PENDING_SHARE_AUDIO_URI_KEY = "decime_pending_share_audio_uri";
const PENDING_SHARE_ERROR_KEY = "decime_pending_share_error";

export const QUICK_REPLY_PATH = "/app/quick-reply/";

async function readPreference(key: string): Promise<string | null> {
  const { Preferences } = await import("@capacitor/preferences");
  const { value } = await Preferences.get({ key });
  return value ?? null;
}

async function removePreference(key: string): Promise<void> {
  const { Preferences } = await import("@capacitor/preferences");
  await Preferences.remove({ key });
}

/** Capacitor Android/iOS serves bundled assets from https://localhost (not Next.js :3000). */
export function isCapacitorAppShell(): boolean {
  if (typeof window === "undefined") {
    return false;
  }

  const { protocol, hostname, port } = window.location;

  // Next.js dev / local web — never treat as Capacitor shell
  if (port === "3000" || port === "3001") {
    return false;
  }

  const capacitor = (window as Window & { Capacitor?: { isNativePlatform?: () => boolean } }).Capacitor;
  if (capacitor?.isNativePlatform?.()) {
    return true;
  }

  if (protocol === "capacitor:" || protocol === "ionic:") {
    return true;
  }

  return (
    (hostname === "localhost" || hostname === "127.0.0.1") &&
    protocol === "https:"
  );
}

export function isNativePlatform(): boolean {
  if (typeof window === "undefined") {
    return false;
  }
  if (Capacitor.isNativePlatform()) {
    return true;
  }
  return isCapacitorAppShell();
}

export function normalizeNativePath(href: string): string | null {
  return normalizeAppPath(href);
}

export function openNativePath(path: string): void {
  const normalized = normalizeAppPath(path);
  if (!normalized || typeof window === "undefined") {
    return;
  }
  const currentPath = normalizeAppPath(window.location.pathname) ?? window.location.pathname;
  if (currentPath === normalized) {
    return;
  }
  navigateInApp(path.includes("?") || path.includes("#") ? path : normalized);
}

export function installCapacitorNavigationFix(): () => void {
  const onClick = (event: MouseEvent) => {
    const anchor = (event.target as Element | null)?.closest("a[href]");
    if (!anchor) {
      return;
    }

    const href = anchor.getAttribute("href");
    if (!href || href.startsWith("http") || href.startsWith("mailto:") || href.startsWith("tel:")) {
      return;
    }

    const path = normalizeNativePath(href);
    if (!path) {
      return;
    }

    event.preventDefault();
    event.stopPropagation();
    openNativePath(path);
  };

  document.addEventListener("click", onClick, true);
  patchInternalAnchorHrefs();
  const removeHrefObserver = installCapacitorAnchorHrefObserver();

  return () => {
    document.removeEventListener("click", onClick, true);
    removeHrefObserver();
  };
}

export async function shareReplyText(text: string, dialogTitle = "Share reply"): Promise<void> {
  const { Share } = await import("@capacitor/share");
  await Share.share({
    text,
    dialogTitle,
  });
}

export async function peekPendingShareText(): Promise<string | null> {
  if (!isNativePlatform()) {
    return null;
  }
  return readPreference(PENDING_SHARE_TEXT_KEY);
}

export async function peekPendingShareAudioUri(): Promise<string | null> {
  if (!isNativePlatform()) {
    return null;
  }
  return readPreference(PENDING_SHARE_AUDIO_URI_KEY);
}

export async function peekForceQuickReply(): Promise<boolean> {
  if (!isNativePlatform()) {
    return false;
  }
  const value = await readPreference(FORCE_QUICK_REPLY_KEY);
  return value === "1";
}

export async function clearForceQuickReply(): Promise<void> {
  if (!isNativePlatform()) {
    return;
  }
  await removePreference(FORCE_QUICK_REPLY_KEY);
}

export async function consumePendingShareText(): Promise<string | null> {
  if (!isNativePlatform()) {
    return null;
  }
  const value = await readPreference(PENDING_SHARE_TEXT_KEY);
  if (!value) {
    return null;
  }
  await removePreference(PENDING_SHARE_TEXT_KEY);
  return value;
}

export async function consumePendingShareAudioUri(): Promise<string | null> {
  if (!isNativePlatform()) {
    return null;
  }
  const value = await readPreference(PENDING_SHARE_AUDIO_URI_KEY);
  if (!value) {
    return null;
  }
  await removePreference(PENDING_SHARE_AUDIO_URI_KEY);
  return value;
}

export async function consumePendingShareError(): Promise<string | null> {
  if (!isNativePlatform()) {
    return null;
  }
  const value = await readPreference(PENDING_SHARE_ERROR_KEY);
  if (!value) {
    return null;
  }
  await removePreference(PENDING_SHARE_ERROR_KEY);
  return value;
}

export function isOnQuickReplyPage(): boolean {
  if (typeof window === "undefined") {
    return false;
  }
  return window.location.pathname.includes("/app/quick-reply");
}

export async function clearStaleSharePrefsIfNotForced(): Promise<void> {
  if (!isNativePlatform()) {
    return;
  }
  if (await peekForceQuickReply()) {
    return;
  }
  await Promise.all([
    removePreference(PENDING_SHARE_TEXT_KEY),
    removePreference(PENDING_SHARE_AUDIO_URI_KEY),
    removePreference(PENDING_SHARE_ERROR_KEY),
  ]);
}

export async function routeToQuickReplyIfPendingShare(): Promise<boolean> {
  if (!isNativePlatform() || typeof window === "undefined") {
    return false;
  }
  if (isOnQuickReplyPage()) {
    return false;
  }

  const forceQuickReply = await peekForceQuickReply();
  if (!forceQuickReply) {
    return false;
  }

  const [text, audio, shareError] = await Promise.all([
    peekPendingShareText(),
    peekPendingShareAudioUri(),
    readPreference(PENDING_SHARE_ERROR_KEY),
  ]);

  if (!text && !audio && !shareError) {
    await clearForceQuickReply();
    return false;
  }

  openNativePath(QUICK_REPLY_PATH);
  return true;
}

export {
  FORCE_QUICK_REPLY_KEY,
  PENDING_SHARE_AUDIO_URI_KEY,
  PENDING_SHARE_ERROR_KEY,
  PENDING_SHARE_TEXT_KEY,
};
