import type {
  TranslateToEsRequest,
  TranslateToEsResponse,
  HistoryListResponse,
} from "@/types/compose";
import type { UnderstandTextRequest, UnderstandTextResponse } from "@/types/incoming";

import { getAuthHeaders, handleUnauthorizedResponse } from "@/lib/auth";
import { getApiBaseUrl, joinApiPath } from "@/lib/api-config";
import { decimeHttpFetch } from "@/lib/native-http";
import { nativeMultipartUpload, shouldUseNativeMultipart } from "@/lib/native-audio-upload";

export { getApiBaseUrl, resolveMediaUrl, setApiBaseUrl } from "@/lib/api-config";

function parseApiErrorDetail(raw: string): string | null {
  if (!raw) {
    return null;
  }
  try {
    const parsed = JSON.parse(raw) as { detail?: unknown };
    const detail = parsed.detail;
    if (typeof detail === "string") {
      return detail;
    }
    if (Array.isArray(detail)) {
      return detail
        .map((item) => (typeof item === "object" && item && "msg" in item ? String(item.msg) : String(item)))
        .join("; ");
    }
  } catch {
    // Not JSON — fall through to raw text.
  }
  return raw;
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const baseUrl = await getApiBaseUrl();
  if (!baseUrl) {
    throw new Error(
      "API не настроен. Откройте «Связь с ПК» и укажите http://IP_ПК:8000 (та же Wi‑Fi, API с --host 0.0.0.0)",
    );
  }
  let response: Response;
  const authHeaders = await getAuthHeaders();
  try {
    response = await decimeHttpFetch(joinApiPath(baseUrl, path), {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...authHeaders,
        ...(init?.headers ?? {}),
      },
    });
  } catch (networkError) {
    const message = networkError instanceof Error ? networkError.message : "Network error";
    if (message.includes("failed to connect") || message.includes("Телефон не достучался")) {
      throw new Error(message);
    }
    throw new Error(`${message} (API: ${baseUrl})`);
  }

  if (response.status === 401) {
    await handleUnauthorizedResponse();
    throw new Error("Session expired. Please sign in again.");
  }

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(parseApiErrorDetail(detail) || `Request failed: ${response.status}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const text = await response.text();
  if (!text) {
    return undefined as T;
  }
  return JSON.parse(text) as T;
}

export async function fetchHealth(): Promise<Record<string, string>> {
  const baseUrl = await getApiBaseUrl();
  const response = await decimeHttpFetch(joinApiPath(baseUrl, "/health"), { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Health check failed: ${response.status}`);
  }
  return response.json();
}

export async function translateToEsuy(
  payload: TranslateToEsRequest,
): Promise<TranslateToEsResponse> {
  return apiFetch<TranslateToEsResponse>("/api/v1/translate/text", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function understandIncomingText(
  payload: UnderstandTextRequest,
): Promise<UnderstandTextResponse> {
  return apiFetch<UnderstandTextResponse>("/api/v1/incoming/understand-text", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function fetchHistory(limit = 20): Promise<HistoryListResponse> {
  return apiFetch<HistoryListResponse>(`/api/v1/history?limit=${limit}`, {
    cache: "no-store",
  });
}

export async function clearHistory(): Promise<{ status: string; message: string }> {
  return apiFetch<{ status: string; message: string }>("/api/v1/history", {
    method: "DELETE",
  });
}

export interface TranscribeAudioResponse {
  audio_id: string;
  transcript_id: string;
  language: string;
  transcript: string;
  confidence_notes: string[];
}

export async function transcribeAudio(
  file: File,
  languageHint: string,
  sourceType: string,
  options?: { filePath?: string | null },
): Promise<TranscribeAudioResponse> {
  const fields = {
    language_hint: languageHint,
    source_type: sourceType,
  };

  if (shouldUseNativeMultipart()) {
    const result = await nativeMultipartUpload("/api/v1/audio/transcribe", {
      filePath: options?.filePath,
      file,
      fileName: file.name,
      mimeType: file.type || undefined,
      fields,
    });
    if (result.status === 401) {
      await handleUnauthorizedResponse();
      throw new Error("Session expired. Please sign in again.");
    }
    if (result.status < 200 || result.status >= 300) {
      throw new Error(parseApiErrorDetail(result.body) || `Transcribe failed: ${result.status}`);
    }
    try {
      return JSON.parse(result.body) as TranscribeAudioResponse;
    } catch {
      throw new Error(`Transcribe returned invalid JSON (HTTP ${result.status})`);
    }
  }

  const form = new FormData();
  form.append("file", file);
  form.append("language_hint", languageHint);
  form.append("source_type", sourceType);

  const baseUrl = await getApiBaseUrl();
  if (!baseUrl) {
    throw new Error(
      "API не настроен. Укажите IP ПК в диалоге при запуске (http://192.168.x.x:8000).",
    );
  }
  const authHeaders = await getAuthHeaders();
  const response = await decimeHttpFetch(joinApiPath(baseUrl, "/api/v1/audio/transcribe"), {
    method: "POST",
    headers: authHeaders,
    body: form,
  });

  if (response.status === 401) {
    await handleUnauthorizedResponse();
    throw new Error("Session expired. Please sign in again.");
  }

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(parseApiErrorDetail(detail) || `Transcribe failed: ${response.status}`);
  }

  return response.json();
}

import type {
  AddToVocabRequest,
  AddToVocabResponse,
  ApproveCandidatesRequest,
  ApproveCandidatesResponse,
  ExtractCandidatesRequest,
  ExtractCandidatesResponse,
  ItemAudioResponse,
  ReviewNextResponse,
  ReviewSubmitRequest,
  ReviewSubmitResponse,
  SheetsJobAcceptedResponse,
  SheetsJobStatusResponse,
  TrainingItemsResponse,
  TrainingListSummary,
} from "@/types/training";
import type { TranslationRatingRequest, TranslationRatingResponse } from "@/types/feedback";

export async function extractCandidates(
  payload: ExtractCandidatesRequest,
): Promise<ExtractCandidatesResponse> {
  return apiFetch<ExtractCandidatesResponse>("/api/v1/training/extract-candidates", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function approveCandidates(
  payload: ApproveCandidatesRequest,
): Promise<ApproveCandidatesResponse> {
  return apiFetch<ApproveCandidatesResponse>("/api/v1/training/approve-candidates", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function addToVocab(payload: AddToVocabRequest): Promise<AddToVocabResponse> {
  return apiFetch<AddToVocabResponse>("/api/v1/training/add-to-vocab", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function deleteTrainingItem(itemId: string): Promise<void> {
  await apiFetch<void>(`/api/v1/training/items/${encodeURIComponent(itemId)}`, {
    method: "DELETE",
  });
}

export async function generateTrainingItemAudio(
  itemId: string,
  options?: { text?: string; locale?: string },
): Promise<ItemAudioResponse> {
  // Orpheus often exceeds Cloudflare's ~100s limit on a blocking POST.
  // Warm via async synthesize (job polling) first, then attach — cache hit is fast.
  const text = options?.text?.trim();
  if (text) {
    await synthesizeAudio(text, {
      locale: options?.locale ?? "es-UY-montevideo",
      mode: "training_reference",
      speed: "normal",
    });
  }
  return apiFetch<ItemAudioResponse>(
    `/api/v1/training/items/${encodeURIComponent(itemId)}/audio`,
    { method: "POST" },
  );
}

export async function fetchTrainingLists(): Promise<TrainingListSummary[]> {
  return apiFetch<TrainingListSummary[]>("/api/v1/training/lists", { cache: "no-store" });
}

export async function fetchTrainingItems(listId: string): Promise<TrainingItemsResponse> {
  return apiFetch<TrainingItemsResponse>(
    `/api/v1/training/items?list_id=${encodeURIComponent(listId)}`,
    { cache: "no-store" },
  );
}

export async function submitTranslationRating(
  payload: TranslationRatingRequest,
): Promise<TranslationRatingResponse> {
  return apiFetch<TranslationRatingResponse>("/api/v1/feedback/translation-rating", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function fetchReviewNext(
  listId: string,
  limit = 20,
): Promise<ReviewNextResponse> {
  return apiFetch<ReviewNextResponse>(
    `/api/v1/training/review/next?list_id=${encodeURIComponent(listId)}&limit=${limit}`,
    { cache: "no-store" },
  );
}

export async function submitReview(
  payload: ReviewSubmitRequest,
): Promise<ReviewSubmitResponse> {
  return apiFetch<ReviewSubmitResponse>("/api/v1/training/review/submit", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function exportDictionaryToSheets(
  listId: string,
): Promise<SheetsJobAcceptedResponse> {
  return apiFetch<SheetsJobAcceptedResponse>("/api/v1/training/sheets/export", {
    method: "POST",
    body: JSON.stringify({ list_id: listId }),
  });
}

export async function importDictionaryFromSheets(payload: {
  list_id: string;
  source_spreadsheet_id: string;
  source_sheet_name: string;
}): Promise<SheetsJobAcceptedResponse> {
  return apiFetch<SheetsJobAcceptedResponse>("/api/v1/training/sheets/import", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function fetchSheetsJob(jobId: string): Promise<SheetsJobStatusResponse> {
  return apiFetch<SheetsJobStatusResponse>(
    `/api/v1/training/sheets/jobs/${encodeURIComponent(jobId)}`,
    { cache: "no-store" },
  );
}

/** Poll sheets job until terminal status or timeout. */
export async function waitForSheetsJob(
  jobId: string,
  options?: { timeoutMs?: number; intervalMs?: number },
): Promise<SheetsJobStatusResponse> {
  const timeoutMs = options?.timeoutMs ?? 10 * 60 * 1000;
  const intervalMs = options?.intervalMs ?? 2000;
  const deadline = Date.now() + timeoutMs;
  let last: SheetsJobStatusResponse | null = null;
  while (Date.now() < deadline) {
    last = await fetchSheetsJob(jobId);
    if (last.status === "completed" || last.status === "failed") {
      return last;
    }
    await new Promise((resolve) => window.setTimeout(resolve, intervalMs));
  }
  if (last) {
    return last;
  }
  throw new Error("Sheets job timed out");
}

export interface SynthesizeAudioResponse {
  audio_id: string;
  audio_url: string;
  cached: boolean;
  status?: "pending" | "ready" | "error";
  job_id?: string | null;
  error?: string | null;
}

export interface SynthesizeJobStatus {
  job_id: string;
  status: "pending" | "ready" | "error";
  audio_id: string;
  audio_url: string;
  cached: boolean;
  error?: string | null;
}

export async function synthesizeAudio(
  text: string,
  options?: { locale?: string; mode?: string; speed?: string },
): Promise<SynthesizeAudioResponse> {
  const started = await apiFetch<SynthesizeAudioResponse>("/api/v1/audio/synthesize", {
    method: "POST",
    body: JSON.stringify({
      text,
      locale: options?.locale ?? "es-UY-montevideo",
      mode: options?.mode ?? "reply",
      speed: options?.speed ?? "normal",
    }),
  });

  if (started.status !== "pending" || !started.job_id) {
    return started;
  }

  // Orpheus on 2 vCPU often exceeds Cloudflare's ~100s proxy limit if we wait on POST.
  const deadline = Date.now() + 5 * 60 * 1000;
  while (Date.now() < deadline) {
    await new Promise((resolve) => window.setTimeout(resolve, 2000));
    const job = await apiFetch<SynthesizeJobStatus>(
      `/api/v1/audio/synthesize/jobs/${encodeURIComponent(started.job_id)}`,
      { cache: "no-store" },
    );
    if (job.status === "ready") {
      return {
        audio_id: job.audio_id,
        audio_url: job.audio_url,
        cached: job.cached,
        status: "ready",
        job_id: job.job_id,
      };
    }
    if (job.status === "error") {
      throw new Error(job.error || "TTS generation failed");
    }
  }
  throw new Error("TTS is still generating. Try Play audio again in a minute.");
}

export async function fetchMediaBlob(url: string): Promise<Blob> {
  const authHeaders = await getAuthHeaders();
  const response = await decimeHttpFetch(url, {
    method: "GET",
    headers: authHeaders,
    cache: "no-store",
  });
  if (response.status === 401) {
    await handleUnauthorizedResponse();
    throw new Error("Session expired. Please sign in again.");
  }
  if (!response.ok) {
    throw new Error(`Audio file request failed: ${response.status}`);
  }
  const buffer = await response.arrayBuffer();
  const headerType = (response.headers.get("content-type") || "").split(";")[0].trim();
  const mimeType =
    headerType && !headerType.includes("json") && !headerType.includes("text/plain")
      ? headerType
      : guessAudioMimeFromUrl(url);
  return new Blob([buffer], { type: mimeType });
}

function guessAudioMimeFromUrl(url: string): string {
  const path = url.split("?")[0].toLowerCase();
  if (path.endsWith(".mp3") || path.endsWith(".mpeg")) {
    return "audio/mpeg";
  }
  if (path.endsWith(".ogg") || path.endsWith(".opus")) {
    return "audio/ogg";
  }
  if (path.endsWith(".webm")) {
    return "audio/webm";
  }
  if (path.endsWith(".m4a") || path.endsWith(".mp4")) {
    return "audio/mp4";
  }
  return "audio/wav";
}
