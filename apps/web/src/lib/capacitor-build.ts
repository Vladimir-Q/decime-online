import { isHttpsApiUrl, PRODUCTION_API_BASE_URL } from "@/lib/production-api";

/** True for APK/static export builds (`npm run build:cap`). Baked in at compile time. */
export function isCapacitorMobileBuild(): boolean {
  return process.env.NEXT_PUBLIC_CAPACITOR_BUILD === "1";
}

/** Mobile build targeting the public HTTPS API (release APK). */
export function isProductionMobileBuild(): boolean {
  if (!isCapacitorMobileBuild()) {
    return false;
  }
  const configured = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
  if (configured) {
    return isHttpsApiUrl(configured);
  }
  return false;
}

export function getMobileBuildDefaultApiUrl(): string {
  const configured = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
  if (configured) {
    return configured.replace(/\/+$/, "");
  }
  if (isProductionMobileBuild()) {
    return PRODUCTION_API_BASE_URL;
  }
  if (isCapacitorMobileBuild()) {
    return "";
  }
  return "http://localhost:8000";
}
