import { isCapacitorMobileBuild } from "@/lib/capacitor-build";
import { DecimeApi } from "@/lib/decime-api-plugin";
import { isNativePlatform } from "@/lib/native-share";

export function shouldUseNativeHttp(): boolean {
  return isCapacitorMobileBuild() || isNativePlatform();
}

function collectHeaders(init?: RequestInit): Record<string, string> {
  const headers: Record<string, string> = {};
  if (!init?.headers) {
    return headers;
  }

  if (init.headers instanceof Headers) {
    init.headers.forEach((value, key) => {
      headers[key] = value;
    });
    return headers;
  }

  if (Array.isArray(init.headers)) {
    for (const [key, value] of init.headers) {
      headers[key] = value;
    }
    return headers;
  }

  return { ...init.headers };
}

export async function decimeHttpFetch(url: string, init?: RequestInit): Promise<Response> {
  if (!shouldUseNativeHttp()) {
    return fetch(url, init);
  }

  const rawBody = init?.body;

  if (rawBody instanceof FormData) {
    return fetch(url, init);
  }

  const method = (init?.method ?? "GET").toUpperCase();
  const headers = collectHeaders(init);
  const body = typeof rawBody === "string" ? rawBody : undefined;

  try {
    const result = await DecimeApi.request({ url, method, headers, body });
    const contentType =
      result.contentType ||
      headers["Content-Type"] ||
      headers["content-type"] ||
      "application/json";

    if (result.bodyBase64) {
      const binary = Uint8Array.from(atob(result.bodyBase64), (c) => c.charCodeAt(0));
      return new Response(binary, {
        status: result.status,
        headers: { "Content-Type": contentType },
      });
    }

    return new Response(result.body ?? "", {
      status: result.status,
      headers: { "Content-Type": contentType },
    });
  } catch (nativeError) {
    const message = nativeError instanceof Error ? nativeError.message : "Native HTTP failed";
    throw new Error(`${message} (${url})`);
  }
}

export async function decimeHttpJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await decimeHttpFetch(url, init);
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `HTTP ${response.status}`);
  }
  return response.json() as Promise<T>;
}
