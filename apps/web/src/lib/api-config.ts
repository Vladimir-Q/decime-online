import { getMobileBuildDefaultApiUrl, isCapacitorMobileBuild, isProductionMobileBuild } from "@/lib/capacitor-build";
import { isHttpsApiUrl } from "@/lib/production-api";
import { readNativeApiUrl, scanNativeLan } from "@/lib/decime-api-native";
import { isNativePlatform } from "@/lib/native-share";
import { decimeHttpFetch } from "@/lib/native-http";

const STORAGE_KEY = "decime_api_base_url";

/** Old docs example IP — never use as a real PC address. */
const STALE_EXAMPLE_HOSTS = new Set(["192.168.1.5"]);

const BUILD_DEFAULT = getMobileBuildDefaultApiUrl();

declare global {
  interface Window {
    __DECIME_API_BASE_URL__?: string;
  }
}

function readInjectedApiUrl(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  const injected = window.__DECIME_API_BASE_URL__?.trim();
  if (!injected) {
    return null;
  }
  return normalizeApiBaseUrl(injected);
}

function shouldUseNativeStorage(): boolean {
  return isCapacitorMobileBuild() || isNativePlatform();
}

let memoryUrl: string | null = null;
let initPromise: Promise<string> | null = null;

export interface DecimeHealth {
  status: string;
  app: string;
  env?: string;
  llm_provider?: string;
  llm_model?: string;
  stt_provider?: string;
  stt_model?: string;
  tts_provider?: string;
  tts_model?: string;
}

export interface LanScanResult {
  url: string;
  app: string;
  env: string;
}

export function normalizeApiBaseUrl(input: string): string {
  let url = input.trim().replace(/^\/+/, "");
  if (!url) {
    return shouldUseNativeStorage() ? "" : BUILD_DEFAULT;
  }
  if (!/^https?:\/\//i.test(url)) {
    url = `http://${url}`;
  }
  url = url.replace(/:\/\/\/+/g, "://");
  return url.replace(/\/+$/, "");
}

export function joinApiPath(baseUrl: string, path: string): string {
  const base = normalizeApiBaseUrl(baseUrl).replace(/\/+$/, "");
  const suffix = path.startsWith("/") ? path : `/${path}`;
  return `${base}${suffix}`;
}

export function getDefaultApiBaseUrl(): string {
  return BUILD_DEFAULT;
}

export function isLoopbackApiUrl(url: string): boolean {
  return /localhost|127\.0\.0\.1/i.test(url);
}

export function isStaleExampleApiUrl(url: string): boolean {
  const normalized = normalizeApiBaseUrl(url);
  if (!normalized) {
    return false;
  }
  try {
    const host = new URL(normalized).hostname;
    return STALE_EXAMPLE_HOSTS.has(host);
  } catch {
    return STALE_EXAMPLE_HOSTS.has(normalized);
  }
}

function isUsableMobileApiUrl(url: string | null | undefined): boolean {
  if (!url?.trim()) {
    return false;
  }
  const normalized = normalizeApiBaseUrl(url);
  return Boolean(normalized) && !isLoopbackApiUrl(normalized) && !isStaleExampleApiUrl(normalized);
}

async function syncMobileApiUrl(normalized: string, options?: { skipNativeWrite?: boolean }): Promise<void> {
  if (typeof window === "undefined" || !shouldUseNativeStorage()) {
    return;
  }
  if (memoryUrl === normalized && window.__DECIME_API_BASE_URL__ === normalized) {
    return;
  }
  memoryUrl = normalized;
  window.__DECIME_API_BASE_URL__ = normalized;
  try {
    localStorage.setItem(STORAGE_KEY, normalized);
  } catch {
    // Ignore WebView storage errors.
  }
  try {
    const { Preferences } = await import("@capacitor/preferences");
    await Preferences.set({ key: STORAGE_KEY, value: normalized });
  } catch {
    // Ignore preference errors.
  }
  if (!options?.skipNativeWrite) {
    try {
      const { DecimeApi } = await import("@/lib/decime-api-plugin");
      await DecimeApi.setApiUrl({ url: normalized });
    } catch {
      // Plugin may be unavailable in web dev.
    }
  }
}

export async function clearApiBaseUrl(): Promise<void> {
  memoryUrl = null;
  initPromise = null;
  if (typeof window === "undefined") {
    return;
  }
  delete window.__DECIME_API_BASE_URL__;
  try {
    if (shouldUseNativeStorage()) {
      const { Preferences } = await import("@capacitor/preferences");
      await Preferences.remove({ key: STORAGE_KEY });
      try {
        const { DecimeApi } = await import("@/lib/decime-api-plugin");
        await DecimeApi.setApiUrl({ url: "" });
      } catch {
        // Plugin may be unavailable in web dev.
      }
    }
  } catch {
    // Ignore preference errors.
  }
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    // Ignore storage errors.
  }
  window.dispatchEvent(new CustomEvent("decime-api-url", { detail: { url: "" } }));
}

export async function migrateStaleApiUrl(): Promise<void> {
  if (!shouldUseNativeStorage()) {
    const current = memoryUrl ?? (typeof window !== "undefined" ? localStorage.getItem(STORAGE_KEY) : null);
    if (current && isStaleExampleApiUrl(current)) {
      await clearApiBaseUrl();
    }
    return;
  }

  const candidates: Array<string | null | undefined> = [
    memoryUrl,
    typeof window !== "undefined" ? localStorage.getItem(STORAGE_KEY) : null,
    readInjectedApiUrl(),
  ];

  try {
    const native = await readNativeApiUrl();
    candidates.push(native);
  } catch {
    // Ignore native read errors.
  }

  try {
    const { Preferences } = await import("@capacitor/preferences");
    const { value } = await Preferences.get({ key: STORAGE_KEY });
    candidates.push(value);
  } catch {
    // Ignore preference errors.
  }

  if (candidates.some((candidate) => candidate && isStaleExampleApiUrl(candidate))) {
    await clearApiBaseUrl();
  }

  if (typeof window !== "undefined") {
    const local = localStorage.getItem(STORAGE_KEY);
    if (local && (isStaleExampleApiUrl(local) || isLoopbackApiUrl(local))) {
      localStorage.removeItem(STORAGE_KEY);
    }
  }
}

export async function autoDiscoverApiUrl(): Promise<string | null> {
  if (!shouldUseNativeStorage()) {
    return null;
  }
  const network = await import("@/lib/decime-api-native").then((mod) => mod.readNativeNetworkInfo());
  const subnet = network?.subnetPrefix ?? "192.168.1";
  const results = await scanLanForDecimeApi({ subnetPrefix: subnet, port: 8000 });
  if (results.length === 0) {
    return null;
  }
  return setApiBaseUrl(results[0].url);
}

export function resetApiBaseUrlCache(): void {
  memoryUrl = null;
  initPromise = null;
}

async function loadStoredUrl(): Promise<string> {
  if (typeof window === "undefined") {
    return BUILD_DEFAULT;
  }

  const injected = readInjectedApiUrl();
  if (injected && !isLoopbackApiUrl(injected)) {
    memoryUrl = injected;
    return memoryUrl;
  }

  try {
    if (shouldUseNativeStorage()) {
      const { Preferences } = await import("@capacitor/preferences");
      const { value } = await Preferences.get({ key: STORAGE_KEY });
      memoryUrl = value ? normalizeApiBaseUrl(value) : BUILD_DEFAULT;
    } else {
      const stored = localStorage.getItem(STORAGE_KEY);
      memoryUrl = stored ? normalizeApiBaseUrl(stored) : BUILD_DEFAULT;
    }
  } catch {
    const stored = localStorage.getItem(STORAGE_KEY);
    memoryUrl = stored ? normalizeApiBaseUrl(stored) : BUILD_DEFAULT;
  }

  if (memoryUrl && isStaleExampleApiUrl(memoryUrl)) {
    memoryUrl = shouldUseNativeStorage() ? "" : BUILD_DEFAULT;
    if (typeof window !== "undefined") {
      void clearApiBaseUrl();
    }
  }

  const injectedAfter = readInjectedApiUrl();
  if (injectedAfter && !isLoopbackApiUrl(injectedAfter)) {
    memoryUrl = injectedAfter;
  }

  return memoryUrl;
}

async function readNativeStoredUrl(): Promise<string | null> {
  const native = await readNativeApiUrl();
  if (isUsableMobileApiUrl(native)) {
    const normalized = normalizeApiBaseUrl(native!);
    await syncMobileApiUrl(normalized, { skipNativeWrite: true });
    return normalized;
  }

  if (typeof window !== "undefined") {
    try {
      const { Preferences } = await import("@capacitor/preferences");
      const { value } = await Preferences.get({ key: STORAGE_KEY });
      if (isUsableMobileApiUrl(value)) {
        const normalized = normalizeApiBaseUrl(value!);
        await syncMobileApiUrl(normalized);
        return normalized;
      }
    } catch {
      // Ignore preference errors.
    }

    const local = localStorage.getItem(STORAGE_KEY);
    if (local && (isStaleExampleApiUrl(local) || isLoopbackApiUrl(local))) {
      localStorage.removeItem(STORAGE_KEY);
    } else if (isUsableMobileApiUrl(local)) {
      const normalized = normalizeApiBaseUrl(local!);
      await syncMobileApiUrl(normalized);
      return normalized;
    }
  }

  const injected = readInjectedApiUrl();
  if (injected && isUsableMobileApiUrl(injected)) {
    await syncMobileApiUrl(injected);
    return injected;
  }

  return null;
}

export async function getApiBaseUrl(): Promise<string> {
  if (shouldUseNativeStorage()) {
    const resolved = await readNativeStoredUrl();
    if (resolved) {
      memoryUrl = resolved;
      if (typeof window !== "undefined") {
        window.__DECIME_API_BASE_URL__ = resolved;
      }
      return resolved;
    }

    if (BUILD_DEFAULT && !isLoopbackApiUrl(BUILD_DEFAULT)) {
      await syncMobileApiUrl(BUILD_DEFAULT);
      return BUILD_DEFAULT;
    }

    if (!isProductionMobileBuild()) {
      const discovered = await autoDiscoverApiUrl();
      if (discovered) {
        return discovered;
      }
    }
    return BUILD_DEFAULT && !isLoopbackApiUrl(BUILD_DEFAULT) ? BUILD_DEFAULT : "";
  }

  if (typeof window !== "undefined") {
    const injected = readInjectedApiUrl();
    if (injected && !isLoopbackApiUrl(injected)) {
      memoryUrl = injected;
      return injected;
    }

    const local = localStorage.getItem(STORAGE_KEY);
    if (local) {
      const normalizedLocal = normalizeApiBaseUrl(local);
      if (!isLoopbackApiUrl(normalizedLocal)) {
        memoryUrl = normalizedLocal;
        return normalizedLocal;
      }
    }
  }

  if (memoryUrl && !isLoopbackApiUrl(memoryUrl)) {
    return memoryUrl;
  }

  resetApiBaseUrlCache();
  initPromise = loadStoredUrl();
  const loaded = await initPromise;
  return isLoopbackApiUrl(loaded) && shouldUseNativeStorage() ? "" : loaded;
}

export async function setApiBaseUrl(url: string): Promise<string> {
  const normalized = normalizeApiBaseUrl(url);
  memoryUrl = normalized;
  initPromise = Promise.resolve(normalized);

  if (typeof window !== "undefined") {
    window.__DECIME_API_BASE_URL__ = normalized;
    if (shouldUseNativeStorage()) {
      const { Preferences } = await import("@capacitor/preferences");
      await Preferences.set({ key: STORAGE_KEY, value: normalized });
      try {
        const { DecimeApi } = await import("@/lib/decime-api-plugin");
        await DecimeApi.setApiUrl({ url: normalized });
      } catch {
        // Plugin may be unavailable in web dev.
      }
    }
    localStorage.setItem(STORAGE_KEY, normalized);
    window.dispatchEvent(new CustomEvent("decime-api-url", { detail: { url: normalized } }));
  }

  return normalized;
}

export function resolveMediaUrl(url: string | null | undefined): string | null {
  if (!url) {
    return null;
  }

  const base = memoryUrl ?? BUILD_DEFAULT;

  if (url.startsWith("/")) {
    return `${base}${url}`;
  }

  try {
    const parsed = new URL(url);
    if (parsed.pathname.startsWith("/api/v1/audio/files/")) {
      return `${base}${parsed.pathname}`;
    }
  } catch {
    return url;
  }

  return url;
}

export async function probeDecimeHealth(baseUrl: string): Promise<DecimeHealth> {
  const url = normalizeApiBaseUrl(baseUrl);
  if (!url) {
    throw new Error("API URL is not configured");
  }
  if (isLoopbackApiUrl(url) && shouldUseNativeStorage()) {
    throw new Error("Enter your PC IP on Wi‑Fi, not localhost");
  }

  const timeoutMs = shouldUseNativeStorage() ? 12000 : 3000;
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await decimeHttpFetch(joinApiPath(url, "/health"), {
      signal: controller.signal,
      cache: "no-store",
    });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const data = (await response.json()) as DecimeHealth;
    if (data.status !== "ok" && !data.app?.toLowerCase().includes("decime")) {
      throw new Error("Not a Decime API");
    }
    return data;
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") {
      throw new Error("Таймаут — проверьте Wi‑Fi и firewall на ПК (порт 8000)");
    }
    throw error;
  } finally {
    window.clearTimeout(timeout);
  }
}

export async function scanLanForDecimeApi(options: {
  subnetPrefix: string;
  port?: number;
  signal?: AbortSignal;
  onProgress?: (checked: number, total: number) => void;
}): Promise<LanScanResult[]> {
  const port = options.port ?? 8000;
  const prefix = options.subnetPrefix.trim().replace(/\.$/, "");
  if (!/^\d{1,3}(\.\d{1,3}){2}$/.test(prefix)) {
    throw new Error("Subnet must look like 192.168.1");
  }

  if (shouldUseNativeStorage()) {
    try {
      const nativeResults = await scanNativeLan({ subnetPrefix: prefix, port });
      if (nativeResults.length > 0) {
        options.onProgress?.(254, 254);
        return nativeResults.map((result) => ({
          url: result.url,
          app: result.app,
          env: result.env ?? "",
        }));
      }
    } catch {
      // Fall through to HTTP scan via DecimeApi.request.
    }
  }

  const hosts = Array.from({ length: 254 }, (_, index) => index + 1);
  const found: LanScanResult[] = [];
  const batchSize = 24;

  for (let start = 0; start < hosts.length; start += batchSize) {
    if (options.signal?.aborted) {
      break;
    }

    const batch = hosts.slice(start, start + batchSize);
    await Promise.all(
      batch.map(async (host) => {
        if (options.signal?.aborted) {
          return;
        }

        const candidate = `http://${prefix}.${host}:${port}`;
        const controller = new AbortController();
        const timeout = window.setTimeout(() => controller.abort(), 900);

        options.signal?.addEventListener("abort", () => controller.abort(), { once: true });

        try {
          const response = await decimeHttpFetch(`${candidate}/health`, {
            signal: controller.signal,
            cache: "no-store",
          });
          if (!response.ok) {
            return;
          }
          const data = (await response.json()) as DecimeHealth;
          if (data.status !== "ok" && !data.app?.toLowerCase().includes("decime")) {
            return;
          }
          found.push({
            url: candidate,
            app: data.app,
            env: data.env ?? "",
          });
        } catch {
          // Ignore unreachable hosts.
        } finally {
          window.clearTimeout(timeout);
        }
      }),
    );

    options.onProgress?.(Math.min(start + batchSize, hosts.length), hosts.length);
  }

  return found.sort((left, right) => left.url.localeCompare(right.url, undefined, { numeric: true }));
}

export function needsLanSetup(url: string): boolean {
  if (!isCapacitorMobileBuild() && !isNativePlatform()) {
    return false;
  }
  if (isProductionMobileBuild() && isHttpsApiUrl(url)) {
    return false;
  }
  return isLoopbackApiUrl(url) || !url.trim();
}

export function isRemoteProductionApi(url: string): boolean {
  const normalized = normalizeApiBaseUrl(url);
  return isHttpsApiUrl(normalized) && !isLoopbackApiUrl(normalized);
}
