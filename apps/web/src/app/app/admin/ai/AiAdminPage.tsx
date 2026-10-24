"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AppNav } from "@/components/AppNav";
import {
  fetchAiPowerStatus,
  fetchCurrentUser,
  setSttPower,
  setTtsPower,
} from "@/lib/auth";
import { isCapacitorMobileBuild } from "@/lib/capacitor-build";
import { navigateInApp } from "@/lib/capacitor-navigation";
import type { AiPowerStatus } from "@/types/admin-ai";

function statusLabel(status: string, enabled: boolean): string {
  if (!enabled && status === "off") {
    return "Off";
  }
  switch (status) {
    case "starting":
      return "Starting…";
    case "warming":
      return "Warming…";
    case "stopping":
      return "Stopping…";
    case "ready":
      return "Ready";
    case "error":
      return "Error";
    case "off":
      return "Off";
    default:
      return status;
  }
}

export function AiAdminPage() {
  const [status, setStatus] = useState<AiPowerStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<"stt" | "tts" | null>(null);
  const [blockedOnMobile, setBlockedOnMobile] = useState(false);

  async function reload() {
    const me = await fetchCurrentUser();
    if (me.role !== "admin") {
      throw new Error("Admin access required");
    }
    setStatus(await fetchAiPowerStatus());
  }

  useEffect(() => {
    if (isCapacitorMobileBuild()) {
      setBlockedOnMobile(true);
      navigateInApp("/app/live/");
      return;
    }
    void reload().catch((loadError) => {
      setError(loadError instanceof Error ? loadError.message : "Could not load AI status");
    });
  }, []);

  if (blockedOnMobile) {
    return (
      <main className="page">
        <p className="muted">Admin console is web-only. Redirecting…</p>
      </main>
    );
  }

  async function toggleStt() {
    if (!status || busy) {
      return;
    }
    setBusy("stt");
    setError(null);
    try {
      setStatus(await setSttPower(!status.stt_enabled));
    } catch (toggleError) {
      setError(toggleError instanceof Error ? toggleError.message : "STT toggle failed");
      await reload().catch(() => undefined);
    } finally {
      setBusy(null);
    }
  }

  async function toggleTts() {
    if (!status || busy) {
      return;
    }
    setBusy("tts");
    setError(null);
    try {
      setStatus(await setTtsPower(!status.tts_enabled));
    } catch (toggleError) {
      setError(toggleError instanceof Error ? toggleError.message : "TTS toggle failed");
      await reload().catch(() => undefined);
    } finally {
      setBusy(null);
    }
  }

  return (
    <main className="page">
      <AppNav isAdmin />
      <section className="hero">
        <p className="eyebrow">Admin</p>
        <h1>AI power</h1>
        <p className="lead">
          Start/stop local speech models. Enabling warms them so Mic and Play audio respond faster.
        </p>
      </section>

      <p className="muted">
        <Link href="/app/admin/users/">Users</Link>
      </p>

      {error ? <p className="error">{error}</p> : null}
      {status?.last_error ? <p className="error">Last error: {status.last_error}</p> : null}

      {!status ? (
        <p className="muted">Loading…</p>
      ) : (
        <>
          <section className="card settings-section">
            <h2>STT (Whisper)</h2>
            <p className="muted">
              Provider: {status.stt_provider}.
              {status.edge_speech
                ? " Edge mode: probes Whisper on your Tailscale PC (does not load into API RAM)."
                : " Loads into API memory when on; unloads when off."}
            </p>
            <p>
              Status: <strong>{statusLabel(status.stt_status, status.stt_enabled)}</strong>
              {status.stt_warm ? " · model warm" : ""}
            </p>
            <button
              type="button"
              className={`button ${status.stt_enabled ? "secondary" : "primary"}`}
              disabled={busy !== null}
              onClick={() => void toggleStt()}
            >
              {busy === "stt"
                ? status.stt_enabled
                  ? "Powering off…"
                  : "Warming…"
                : status.stt_enabled
                  ? "Power off STT"
                  : "Power on + warm STT"}
            </button>
          </section>

          <section className="card settings-section">
            <h2>TTS (Orpheus)</h2>
            <p className="muted">
              Provider: {status.tts_provider}.
              {status.edge_speech
                ? " Edge mode: warms Orpheus/Ollama on your Tailscale PC (no Docker on the VM)."
                : " Starts Ollama + Orpheus containers, then warms the model."}
            </p>
            {status.edge_speech && status.orpheus_tts_base_url ? (
              <p className="muted">
                Edge TTS URL: <code>{status.orpheus_tts_base_url}</code>
              </p>
            ) : null}
            {status.edge_speech && status.openai_stt_base_url ? (
              <p className="muted">
                Edge STT URL: <code>{status.openai_stt_base_url}</code>
              </p>
            ) : null}
            <p>
              Status: <strong>{statusLabel(status.tts_status, status.tts_enabled)}</strong>
              {status.tts_containers_running ? " · ready path" : ""}
            </p>
            {Object.keys(status.tts_containers).length > 0 ? (
              <p className="muted">
                Containers:{" "}
                {Object.entries(status.tts_containers)
                  .map(([name, state]) => `${name}=${state}`)
                  .join(", ")}
              </p>
            ) : null}
            {!status.docker_control_available &&
            status.tts_provider === "orpheus" &&
            !status.edge_speech ? (
              <p className="error">
                Docker control unavailable. Mount docker.sock and set AI_DOCKER_CONTROL_ENABLED=true,
                or switch to Tailscale edge (docs/edge_speech_tailscale.md).
              </p>
            ) : null}
            <button
              type="button"
              className={`button ${status.tts_enabled ? "secondary" : "primary"}`}
              disabled={busy !== null}
              onClick={() => void toggleTts()}
            >
              {busy === "tts"
                ? status.tts_enabled
                  ? "Stopping…"
                  : "Starting + warming…"
                : status.tts_enabled
                  ? "Power off TTS"
                  : "Power on + warm TTS"}
            </button>
            <p className="muted">
              {status.edge_speech
                ? "Keep your PC awake; first warm can still take a minute."
                : "First TTS warm can take several minutes on CPU."}
            </p>
          </section>

          <div className="settings-actions">
            <button
              type="button"
              className="button secondary small"
              disabled={busy !== null}
              onClick={() => {
                setError(null);
                void reload().catch((loadError) => {
                  setError(loadError instanceof Error ? loadError.message : "Refresh failed");
                });
              }}
            >
              Refresh status
            </button>
          </div>
        </>
      )}
    </main>
  );
}
