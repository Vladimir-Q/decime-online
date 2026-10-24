import type {
  AuthConfig,
  AuthTokenResponse,
  LoginRequest,
  RegisterRequest,
  UserCreateRequest,
  UserPreferencesUpdateRequest,
  UserPublic,
  UserUpdateRequest,
} from "@/types/auth";
import type { AiPowerStatus } from "@/types/admin-ai";
import type { AdminDashboardResponse } from "@/types/admin-dashboard";

import { getApiBaseUrl, getDefaultApiBaseUrl, joinApiPath } from "@/lib/api-config";
import { isCapacitorMobileBuild } from "@/lib/capacitor-build";
import { navigateInApp } from "@/lib/capacitor-navigation";
import { decimeHttpFetch } from "@/lib/native-http";

const TOKEN_KEY = "decime_auth_token";
const CONFIG_CACHE_KEY = "decime_auth_config";

export const SESSION_EXPIRED_EVENT = "decime-session-expired";

let cachedConfig: AuthConfig | null = null;

export async function getStoredToken(): Promise<string | null> {
  if (typeof window === "undefined") {
    return null;
  }

  if (isCapacitorMobileBuild()) {
    try {
      const { Preferences } = await import("@capacitor/preferences");
      const { value } = await Preferences.get({ key: TOKEN_KEY });
      if (value) {
        return value;
      }
    } catch {
      // fall through to localStorage
    }
  }

  return localStorage.getItem(TOKEN_KEY);
}

export async function setStoredToken(token: string | null): Promise<void> {
  if (typeof window === "undefined") {
    return;
  }

  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }

  if (isCapacitorMobileBuild()) {
    try {
      const { Preferences } = await import("@capacitor/preferences");
      if (token) {
        await Preferences.set({ key: TOKEN_KEY, value: token });
      } else {
        await Preferences.remove({ key: TOKEN_KEY });
      }
    } catch {
      // ignore
    }
  }
}

export async function getAuthHeaders(): Promise<Record<string, string>> {
  // Always attach a stored JWT when present. Do not gate on /auth/config —
  // a failed config probe must not strip Authorization after a successful login.
  const token = await getStoredToken();
  if (!token) {
    return {};
  }
  return { Authorization: `Bearer ${token}` };
}

export function clearAuthConfigCache(): void {
  cachedConfig = null;
}

export async function invalidateSession(): Promise<void> {
  await setStoredToken(null);
  clearAuthConfigCache();
}

export function redirectToLogin(returnTo?: string): void {
  if (typeof window === "undefined") {
    return;
  }
  const path = returnTo || `${window.location.pathname}${window.location.search}` || "/app/live/";
  const query = `returnTo=${encodeURIComponent(path)}`;
  navigateInApp(`/login/?${query}`);
}

export async function handleUnauthorizedResponse(returnTo?: string): Promise<void> {
  await invalidateSession();
  window.dispatchEvent(new CustomEvent(SESSION_EXPIRED_EVENT));
  redirectToLogin(returnTo);
}

function parseAuthEnabled(value: unknown): boolean {
  return value === true || value === "true";
}

/** Resolve whether the server requires JWT (tries config, then /health, then localhost fallback). */
export async function resolveServerAuthEnabled(): Promise<boolean> {
  const bases = new Set<string>();
  try {
    bases.add(await getApiBaseUrl());
  } catch {
    // ignore
  }
  bases.add(getDefaultApiBaseUrl());

  for (const baseUrl of bases) {
    try {
      const configResponse = await decimeHttpFetch(joinApiPath(baseUrl, "/api/v1/auth/config"), {
        cache: "no-store",
      });
      if (configResponse.ok) {
        cachedConfig = (await configResponse.json()) as AuthConfig;
        return cachedConfig.auth_enabled;
      }
    } catch {
      // try health on same base
    }

    try {
      const healthResponse = await decimeHttpFetch(joinApiPath(baseUrl, "/health"), {
        cache: "no-store",
      });
      if (healthResponse.ok) {
        const health = (await healthResponse.json()) as { auth_enabled?: unknown };
        const enabled = parseAuthEnabled(health.auth_enabled);
        cachedConfig = { auth_enabled: enabled, allow_registration: false };
        return enabled;
      }
    } catch {
      // try next base
    }
  }

  cachedConfig = { auth_enabled: false, allow_registration: false };
  return false;
}

export async function fetchAuthConfig(force = false): Promise<AuthConfig> {
  if (cachedConfig && !force) {
    return cachedConfig;
  }

  try {
    const baseUrl = await getApiBaseUrl();
    const response = await decimeHttpFetch(joinApiPath(baseUrl, "/api/v1/auth/config"), {
      cache: "no-store",
    });
    if (response.ok) {
      cachedConfig = (await response.json()) as AuthConfig;
      if (typeof window !== "undefined") {
        sessionStorage.setItem(CONFIG_CACHE_KEY, JSON.stringify(cachedConfig));
      }
      return cachedConfig;
    }
  } catch {
    // fall through to health-based resolution
  }

  // Never treat a failed config HTTP status as "auth off" — that stripped
  // Authorization headers and bounced the APK back to an empty login form.
  const enabled = await resolveServerAuthEnabled();
  return cachedConfig ?? { auth_enabled: enabled, allow_registration: false };
}

function formatApiError(detail: string, status: number): string {
  const trimmed = detail.trim();
  if (!trimmed) {
    return `Request failed: ${status}`;
  }
  try {
    const parsed = JSON.parse(trimmed) as { detail?: unknown };
    if (typeof parsed.detail === "string") {
      return parsed.detail;
    }
    if (Array.isArray(parsed.detail)) {
      return parsed.detail
        .map((item) => {
          if (typeof item === "string") {
            return item;
          }
          if (item && typeof item === "object" && "msg" in item) {
            return String((item as { msg: unknown }).msg);
          }
          return JSON.stringify(item);
        })
        .join("; ");
    }
  } catch {
    // plain text body
  }
  return trimmed;
}

/** Login/register — must not treat HTTP 401 as "session expired" (that remounts login empty). */
async function publicAuthRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const baseUrl = await getApiBaseUrl();
  if (!baseUrl) {
    throw new Error("API URL is not configured");
  }
  const response = await decimeHttpFetch(joinApiPath(baseUrl, path), {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(formatApiError(detail, response.status));
  }
  return response.json() as Promise<T>;
}

async function authFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const baseUrl = await getApiBaseUrl();
  const authHeaders = await getAuthHeaders();
  const response = await decimeHttpFetch(joinApiPath(baseUrl, path), {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders,
      ...(init?.headers ?? {}),
    },
  });
  if (response.status === 401) {
    await handleUnauthorizedResponse();
    throw new Error("Session expired. Please sign in again.");
  }
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(formatApiError(detail, response.status));
  }
  return response.json() as Promise<T>;
}

export async function login(payload: LoginRequest): Promise<AuthTokenResponse> {
  const result = await publicAuthRequest<AuthTokenResponse>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  if (!result.access_token) {
    throw new Error("Login succeeded but no access token was returned");
  }
  await setStoredToken(result.access_token);
  clearAuthConfigCache();
  return result;
}

export async function register(payload: RegisterRequest): Promise<AuthTokenResponse> {
  const result = await publicAuthRequest<AuthTokenResponse>("/api/v1/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  if (!result.access_token) {
    throw new Error("Registration succeeded but no access token was returned");
  }
  await setStoredToken(result.access_token);
  clearAuthConfigCache();
  return result;
}

export async function logout(): Promise<void> {
  await setStoredToken(null);
  clearAuthConfigCache();
}

export async function fetchCurrentUser(): Promise<UserPublic> {
  return authFetch<UserPublic>("/api/v1/auth/me", { cache: "no-store" });
}

export async function updateMyPreferences(
  payload: UserPreferencesUpdateRequest,
): Promise<UserPublic> {
  return authFetch<UserPublic>("/api/v1/auth/me/preferences", {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function listUsers(): Promise<UserPublic[]> {
  return authFetch<UserPublic[]>("/api/v1/auth/users", { cache: "no-store" });
}

export async function createUser(payload: UserCreateRequest): Promise<UserPublic> {
  return authFetch<UserPublic>("/api/v1/auth/users", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateUser(userId: string, payload: UserUpdateRequest): Promise<UserPublic> {
  return authFetch<UserPublic>(`/api/v1/auth/users/${encodeURIComponent(userId)}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function fetchAiPowerStatus(): Promise<AiPowerStatus> {
  return authFetch<AiPowerStatus>("/api/v1/admin/ai/status", { cache: "no-store" });
}

export async function setSttPower(enabled: boolean): Promise<AiPowerStatus> {
  return authFetch<AiPowerStatus>("/api/v1/admin/ai/stt", {
    method: "POST",
    body: JSON.stringify({ enabled }),
  });
}

export async function setTtsPower(enabled: boolean): Promise<AiPowerStatus> {
  return authFetch<AiPowerStatus>("/api/v1/admin/ai/tts", {
    method: "POST",
    body: JSON.stringify({ enabled }),
  });
}

export async function fetchAdminDashboard(days = 30): Promise<AdminDashboardResponse> {
  return authFetch<AdminDashboardResponse>(
    `/api/v1/admin/dashboard?days=${encodeURIComponent(String(days))}`,
    { cache: "no-store" },
  );
}
