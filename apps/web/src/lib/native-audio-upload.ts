import { getAuthHeaders } from "@/lib/auth";
import { getApiBaseUrl, joinApiPath } from "@/lib/api-config";
import { isCapacitorMobileBuild } from "@/lib/capacitor-build";
import { DecimeApi } from "@/lib/decime-api-plugin";
import { isNativePlatform } from "@/lib/native-share";

export function shouldUseNativeMultipart(): boolean {
  return isCapacitorMobileBuild() || isNativePlatform();
}

/** Capacitor local file URL → absolute path on device */
export function capacitorUriToPath(uri: string): string | null {
  const marker = "_capacitor_file_";
  const index = uri.indexOf(marker);
  if (index === -1) {
    return null;
  }
  return decodeURIComponent(uri.slice(index + marker.length));
}

export async function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result;
      if (typeof result !== "string") {
        reject(new Error("Could not read audio file"));
        return;
      }
      const comma = result.indexOf(",");
      resolve(comma >= 0 ? result.slice(comma + 1) : result);
    };
    reader.onerror = () => reject(reader.error ?? new Error("Could not read audio file"));
    reader.readAsDataURL(file);
  });
}

export function guessMimeType(fileName: string, fallback = "application/octet-stream"): string {
  const lower = fileName.toLowerCase();
  if (lower.endsWith(".ogg") || lower.endsWith(".opus")) {
    return "audio/ogg";
  }
  if (lower.endsWith(".m4a") || lower.endsWith(".aac")) {
    return "audio/mp4";
  }
  if (lower.endsWith(".mp3")) {
    return "audio/mpeg";
  }
  if (lower.endsWith(".wav")) {
    return "audio/wav";
  }
  if (lower.endsWith(".3gp")) {
    return "audio/3gpp";
  }
  return fallback;
}

export async function nativeMultipartUpload(
  endpointPath: string,
  options: {
    filePath?: string | null;
    file?: File;
    fileName?: string;
    mimeType?: string;
    fields?: Record<string, string>;
  },
): Promise<{ status: number; body: string }> {
  const baseUrl = await getApiBaseUrl();
  if (!baseUrl) {
    throw new Error(
      "API не настроен. Укажите IP ПК при запуске (http://192.168.x.x:8000).",
    );
  }
  const url = joinApiPath(baseUrl, endpointPath);
  const fileName = options.fileName ?? options.file?.name ?? "audio.ogg";
  const mimeType = options.mimeType ?? options.file?.type ?? guessMimeType(fileName);
  const authHeaders = await getAuthHeaders();

  if (options.filePath) {
    return DecimeApi.multipartRequest({
      url,
      headers: authHeaders,
      filePath: options.filePath,
      fileName,
      mimeType,
      fields: options.fields,
    });
  }

  if (!options.file) {
    throw new Error("No audio file to upload");
  }

  const fileBase64 = await fileToBase64(options.file);
  return DecimeApi.multipartRequest({
    url,
    headers: authHeaders,
    fileBase64,
    fileName,
    mimeType,
    fields: options.fields,
  });
}
