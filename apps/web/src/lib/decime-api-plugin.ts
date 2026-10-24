import { registerPlugin } from "@capacitor/core";

export interface DecimeApiHttpResponse {
  status: number;
  body: string;
  /** Present when the response body is base64-encoded binary (e.g. audio). */
  bodyBase64?: string;
  contentType?: string;
}

export interface DecimeApiMultipartRequest {
  url: string;
  headers?: Record<string, string>;
  filePath?: string;
  fileBase64?: string;
  fileName?: string;
  mimeType?: string;
  fields?: Record<string, string>;
}

export interface DecimeApiPlugin {
  openApiSetup(): Promise<{ url: string }>;
  getApiUrl(): Promise<{ url: string }>;
  setApiUrl(options: { url: string }): Promise<{ url: string }>;
  getNetworkInfo(): Promise<{ phoneIp: string; subnetPrefix: string }>;
  scanLan(options?: { subnetPrefix?: string; port?: number }): Promise<{
    resultsJson?: string;
    results?: Array<{ url: string; app: string; env: string }>;
  }>;
  probeHealth(options: { url: string }): Promise<{
    ok: boolean;
    app?: string;
    env?: string;
    error?: string;
  }>;
  request(options: {
    url: string;
    method?: string;
    headers?: Record<string, string>;
    body?: string;
  }): Promise<DecimeApiHttpResponse>;
  multipartRequest(options: DecimeApiMultipartRequest): Promise<DecimeApiHttpResponse>;
}

export const DecimeApi = registerPlugin<DecimeApiPlugin>("DecimeApi");
