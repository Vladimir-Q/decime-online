/** Production Decime API — baked into mobile release builds. */
export const PRODUCTION_API_BASE_URL = "https://api.decime.online";

export function isHttpsApiUrl(url: string): boolean {
  return /^https:\/\//i.test(url.trim());
}
