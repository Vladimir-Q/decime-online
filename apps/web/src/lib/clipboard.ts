import { Capacitor } from "@capacitor/core";
import { Clipboard } from "@capacitor/clipboard";

import { isCapacitorMobileBuild } from "@/lib/capacitor-build";
import { isNativePlatform } from "@/lib/native-share";

const AUDIO_MIME_PREFIXES = ["audio/", "video/ogg", "application/ogg"];

function prefersNativeClipboard(): boolean {
  if (typeof window === "undefined") {
    return false;
  }
  if (isCapacitorMobileBuild() || isNativePlatform()) {
    return true;
  }
  try {
    return Capacitor.isNativePlatform();
  } catch {
    return false;
  }
}

function clipboardErrorMessage(error: unknown, fallback: string): string {
  const message = error instanceof Error ? error.message : String(error ?? "");
  if (/permission|denied|NotAllowedError|secure context/i.test(message)) {
    return fallback;
  }
  if (/no data|empty|null/i.test(message)) {
    return fallback;
  }
  return message.trim() || fallback;
}

/** Read plain text from the system clipboard (native Capacitor on Android/iOS). */
export async function readClipboardText(): Promise<string | null> {
  if (prefersNativeClipboard()) {
    try {
      const result = await Clipboard.read();
      const text = result.value?.trim();
      return text || null;
    } catch (nativeError) {
      throw new Error(
        clipboardErrorMessage(
          nativeError,
          "Could not read clipboard. Copy text first, then tap Paste.",
        ),
      );
    }
  }

  if (!navigator.clipboard?.readText) {
    throw new Error("Clipboard read is not supported in this browser.");
  }
  try {
    const text = (await navigator.clipboard.readText()).trim();
    return text || null;
  } catch (webError) {
    throw new Error(
      clipboardErrorMessage(
        webError,
        "Clipboard permission denied. Allow clipboard access or paste manually.",
      ),
    );
  }
}

/**
 * Best-effort audio from clipboard. On native Android/iOS the Web Clipboard API
 * cannot read shared voice notes — callers should fall back to file upload.
 */
export async function readClipboardAudioFile(): Promise<File | null> {
  if (prefersNativeClipboard()) {
    // Capacitor Clipboard is text/image oriented; audio paste is not available natively.
    return null;
  }

  if (!navigator.clipboard?.read) {
    return null;
  }

  try {
    const items = await navigator.clipboard.read();
    for (const item of items) {
      for (const mimeType of item.types) {
        if (
          !AUDIO_MIME_PREFIXES.some(
            (prefix) => mimeType.startsWith(prefix) || mimeType.includes("ogg"),
          )
        ) {
          continue;
        }
        const blob = await item.getType(mimeType);
        const extension = mimeType.includes("ogg") ? "ogg" : mimeType.split("/")[1] || "webm";
        return new File([blob], `clipboard-audio.${extension}`, {
          type: blob.type || mimeType,
        });
      }
    }
    return null;
  } catch (webError) {
    throw new Error(
      clipboardErrorMessage(
        webError,
        "Clipboard audio is not available. Use Upload audio instead.",
      ),
    );
  }
}
