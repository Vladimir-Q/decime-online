"use client";

import { useEffect, useRef, useState } from "react";

import {
  getApiBaseUrl,
  getDefaultApiBaseUrl,
  isLoopbackApiUrl,
  probeDecimeHealth,
  scanLanForDecimeApi,
  setApiBaseUrl,
  type LanScanResult,
} from "@/lib/api-config";
import { isCapacitorMobileBuild } from "@/lib/capacitor-build";
import { canUseNativeApiSetup, openNativeApiSetup, readNativeNetworkInfo } from "@/lib/decime-api-native";
import { isNativePlatform } from "@/lib/native-share";

const SUBNET_PRESETS = ["192.168.1", "192.168.0", "10.0.0"];
const MOBILE_BUILD = isCapacitorMobileBuild();

function formatConnectionError(error: unknown): string {
  const message = error instanceof Error ? error.message : "Connection failed";
  if (message === "Failed to fetch") {
    return "Cannot reach the API. Check Wi‑Fi, firewall, and that the API runs with --host 0.0.0.0.";
  }
  return message;
}

interface ApiConnectionPanelProps {
  /** auto: show only when URL missing or health fails; always: diagnostics page */
  mode?: "auto" | "always";
}

export function ApiConnectionPanel({ mode = "auto" }: ApiConnectionPanelProps) {
  const nativeShell = MOBILE_BUILD || isNativePlatform();
  const forceVisible = mode === "always";
  const [visible, setVisible] = useState(forceVisible || nativeShell);
  const [draftUrl, setDraftUrl] = useState(getDefaultApiBaseUrl());
  const [savedUrl, setSavedUrl] = useState("");
  const [subnetPrefix, setSubnetPrefix] = useState("192.168.1");
  const [port, setPort] = useState("8000");
  const [scanResults, setScanResults] = useState<LanScanResult[]>([]);
  const [scanProgress, setScanProgress] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [phoneIp, setPhoneIp] = useState<string | null>(null);
  const autoScanStarted = useRef(false);

  useEffect(() => {
    if (!nativeShell) {
      return;
    }

    const syncFromNative = () => {
      const injected = window.__DECIME_API_BASE_URL__?.trim();
      if (injected) {
        setSavedUrl(injected);
        setDraftUrl(injected);
        void refreshConnectionState(injected);
      }
    };

    syncFromNative();
    window.addEventListener("decime-api-url", syncFromNative as EventListener);

    void (async () => {
      const current = await getApiBaseUrl();
      setSavedUrl(current);
      setDraftUrl(current || getDefaultApiBaseUrl());

      const network = await readNativeNetworkInfo();
      if (network?.subnetPrefix) {
        setSubnetPrefix(network.subnetPrefix);
        setPhoneIp(network.phoneIp || null);
      }

      const ok = await refreshConnectionState(current);

      if (forceVisible && !autoScanStarted.current && !ok) {
        autoScanStarted.current = true;
        void handleScan(network?.subnetPrefix);
      }
    })();

    return () => {
      window.removeEventListener("decime-api-url", syncFromNative as EventListener);
    };
  }, [nativeShell]);

  async function refreshConnectionState(url: string) {
    if (isLoopbackApiUrl(url)) {
      if (!forceVisible) {
        setVisible(true);
      }
      setError("localhost does not work on a phone. Scan the network or enter your PC Wi‑Fi IP.");
      return false;
    }

    if (!url) {
      if (!forceVisible) {
        setVisible(true);
      }
      setError("Укажите IP ПК или нажмите «Scan network».");
      return false;
    }

    try {
      await probeDecimeHealth(url);
      if (!forceVisible) {
        setVisible(false);
      }
      setError(null);
      return true;
    } catch (probeError) {
      if (!forceVisible) {
        setVisible(true);
      }
      setError(formatConnectionError(probeError));
      return false;
    }
  }

  async function handleSaveAndTest() {
    await handleSaveAndTestWithUrl(draftUrl);
  }

  async function handleUseScanResult(result: LanScanResult) {
    setDraftUrl(result.url);
    await handleSaveAndTestWithUrl(result.url);
  }

  async function handleSaveAndTestWithUrl(url: string) {
    setBusy(true);
    setStatusMessage(null);
    setError(null);
    try {
      const health = await probeDecimeHealth(url);
      const normalized = await setApiBaseUrl(url);
      setSavedUrl(normalized);
      setDraftUrl(normalized);
      setStatusMessage(`Connected: ${health.app}`);
      if (!forceVisible) {
        setVisible(false);
      }
    } catch (saveError) {
      setError(formatConnectionError(saveError));
      if (!forceVisible) {
        setVisible(true);
      }
    } finally {
      setBusy(false);
    }
  }

  async function handleScan(presetSubnet?: string) {
    setScanning(true);
    setScanResults([]);
    setError(null);
    setStatusMessage(null);
    setScanProgress("Starting scan...");

    const controller = new AbortController();
    const activeSubnet = presetSubnet?.trim() || subnetPrefix;
    if (presetSubnet) {
      setSubnetPrefix(presetSubnet);
    }
    try {
      const portNumber = Number(port) || 8000;
      const results = await scanLanForDecimeApi({
        subnetPrefix: activeSubnet,
        port: portNumber,
        signal: controller.signal,
        onProgress: (checked, total) => {
          setScanProgress(`Scanning ${activeSubnet}.x:${portNumber} (${checked}/${total})`);
        },
      });
      setScanResults(results);
      if (results.length === 0) {
        setStatusMessage(
          "Decime API не найден. Проверьте Wi‑Fi, firewall (порт 8000) и uvicorn --host 0.0.0.0.",
        );
      } else if (results.length === 1) {
        setStatusMessage(`Найден ${results[0].url}. Подключаем…`);
        await handleUseScanResult(results[0]);
      } else {
        setStatusMessage(`Найдено серверов: ${results.length}. Выберите ПК с Decime.`);
      }
    } catch (scanError) {
      setError(scanError instanceof Error ? scanError.message : "Scan failed");
    } finally {
      setScanning(false);
      setScanProgress(null);
    }
  }

  if (!nativeShell || (!forceVisible && !visible)) {
    return null;
  }

  return (
    <section className="card settings-warning api-connection-panel">
      <strong>Connect to your PC API</strong>
      <p className="muted">
        Phone and PC must be on the same Wi‑Fi. Start API with{" "}
        <code>uvicorn ... --host 0.0.0.0 --port 8000</code>.
        {phoneIp ? ` Phone IP: ${phoneIp}.` : null}
      </p>
      <label className="field-label" htmlFor="quick-api-url">
        API URL
      </label>
      <input
        id="quick-api-url"
        className="input"
        value={draftUrl}
        onChange={(event) => setDraftUrl(event.target.value)}
        placeholder="http://192.168.1.2:8000"
        autoCapitalize="off"
        autoCorrect="off"
        spellCheck={false}
      />
      <p className="muted">Saved: {savedUrl || "not set yet"}</p>
      <div className="settings-actions">
        <button type="button" className="button primary" disabled={busy} onClick={() => void handleSaveAndTest()}>
          Save & test
        </button>
        {canUseNativeApiSetup() ? (
          <button type="button" className="button secondary" disabled={busy} onClick={() => void openNativeApiSetup()}>
            Изменить IP
          </button>
        ) : null}
      </div>

      <div className="settings-row">
        <label className="field-label" htmlFor="quick-subnet-prefix">
          Scan subnet
        </label>
        <input
          id="quick-subnet-prefix"
          className="input"
          value={subnetPrefix}
          onChange={(event) => setSubnetPrefix(event.target.value)}
          placeholder="192.168.1"
        />
      </div>
      <div className="subnet-presets">
        {SUBNET_PRESETS.map((preset) => (
          <button
            key={preset}
            type="button"
            className="button secondary small"
            disabled={scanning}
            onClick={() => setSubnetPrefix(preset)}
          >
            {preset}.x
          </button>
        ))}
      </div>
      <div className="settings-row">
        <label className="field-label" htmlFor="quick-api-port">
          Port
        </label>
        <input
          id="quick-api-port"
          className="input"
          inputMode="numeric"
          value={port}
          onChange={(event) => setPort(event.target.value)}
        />
      </div>
      <div className="settings-actions">
        <button type="button" className="button secondary" disabled={scanning || busy} onClick={() => void handleScan()}>
          {scanning ? "Scanning..." : "Scan network"}
        </button>
      </div>
      {scanProgress ? <p className="muted">{scanProgress}</p> : null}
      {scanResults.length > 0 ? (
        <ul className="scan-results">
          {scanResults.map((result) => (
            <li key={result.url}>
              <button type="button" className="button secondary small" disabled={busy} onClick={() => void handleUseScanResult(result)}>
                {result.url} — {result.app}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
      {statusMessage ? <p className="status-ok">{statusMessage}</p> : null}
      {error ? <p className="error">{error}</p> : null}
    </section>
  );
}
