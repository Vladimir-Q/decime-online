import { resetApiBaseUrlCache, setApiBaseUrl } from "@/lib/api-config";
import { isCapacitorMobileBuild } from "@/lib/capacitor-build";
import { DecimeApi } from "@/lib/decime-api-plugin";
import { isNativePlatform } from "@/lib/native-share";

export function canUseNativeApiSetup(): boolean {
  return isCapacitorMobileBuild() || isNativePlatform();
}

export async function openNativeApiSetup(): Promise<string | null> {
  if (!canUseNativeApiSetup()) {
    return null;
  }

  try {
    const result = await DecimeApi.openApiSetup();
    const url = result.url?.trim();
    if (!url) {
      return null;
    }
    resetApiBaseUrlCache();
    await setApiBaseUrl(url);
    return url;
  } catch {
    return null;
  }
}

export async function readNativeApiUrl(): Promise<string | null> {
  if (!canUseNativeApiSetup()) {
    return null;
  }

  try {
    const result = await DecimeApi.getApiUrl();
    const url = result.url?.trim();
    return url || null;
  } catch {
    return null;
  }
}

export async function readNativeNetworkInfo(): Promise<{
  phoneIp: string;
  subnetPrefix: string;
} | null> {
  if (!canUseNativeApiSetup()) {
    return null;
  }

  try {
    return await DecimeApi.getNetworkInfo();
  } catch {
    return null;
  }
}

export async function scanNativeLan(options?: {
  subnetPrefix?: string;
  port?: number;
}): Promise<Array<{ url: string; app: string; env: string }>> {
  if (!canUseNativeApiSetup()) {
    return [];
  }

  try {
    const result = await DecimeApi.scanLan(options ?? {});
    if (result.resultsJson) {
      const parsed = JSON.parse(result.resultsJson) as Array<{ url: string; app: string; env: string }>;
      return Array.isArray(parsed) ? parsed : [];
    }
    return result.results ?? [];
  } catch {
    return [];
  }
}

export async function probeNativeHealth(url: string): Promise<{
  ok: boolean;
  app?: string;
  env?: string;
  error?: string;
}> {
  if (!canUseNativeApiSetup()) {
    return { ok: false, error: "Native plugin unavailable" };
  }

  try {
    return await DecimeApi.probeHealth({ url });
  } catch (error) {
    return {
      ok: false,
      error: error instanceof Error ? error.message : "Health check failed",
    };
  }
}
