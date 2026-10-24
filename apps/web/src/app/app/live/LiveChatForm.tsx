"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { AppNav } from "@/components/AppNav";
import { useAppLanguage } from "@/components/AppLanguageProvider";
import { AudioPlayer } from "@/components/AudioPlayer";
import { QuickReplyApiHint } from "@/components/QuickReplyApiHint";
import { AddToVocabButton } from "@/features/training/AddToVocabButton";
import { TranslationRatingControl } from "@/features/feedback/TranslationRatingControl";
import {
  buildMicConstraints,
  getStoredMicDeviceId,
  listAudioInputDevices,
  requestMicPermission,
  storeMicDeviceId,
  type AudioInputDevice,
} from "@/lib/audio-input-devices";
import { translateToEsuy, transcribeAudio, understandIncomingText } from "@/lib/api";
import { isCapacitorMobileBuild } from "@/lib/capacitor-build";
import {
  liveDirectionForLanguage,
  liveDirectionLabel,
  liveSttLanguageHint,
  resolveLiveInputLanguage,
  type LiveInputLanguage,
} from "@/lib/live-detect";
import { isNativePlatform, shareReplyText } from "@/lib/native-share";
import { clampTranslationText, MAX_TRANSLATION_CHARS } from "@/lib/translation-limits";

function formatCharCount(template: string, current: number, max: number): string {
  return template.replace("{current}", String(current)).replace("{max}", String(max));
}

interface LiveOutput {
  text: string;
  direction: "to_es" | "to_explanation";
  sourceLanguage: LiveInputLanguage;
  sourceText: string;
}

function looksLikeRussian(text: string): boolean {
  return /[\u0400-\u04FF]/.test(text) && (text.match(/[\u0400-\u04FF]/g)?.length ?? 0) >= 3;
}

export function LiveChatForm() {
  const { language: explanationLanguage, t } = useAppLanguage();
  const [inputText, setInputText] = useState("");
  const [output, setOutput] = useState<LiveOutput | null>(null);
  const [loading, setLoading] = useState(false);
  const [recording, setRecording] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [nativeShell, setNativeShell] = useState(false);
  const [micDevices, setMicDevices] = useState<AudioInputDevice[]>([]);
  const [selectedMicId, setSelectedMicId] = useState<string>("");
  const [micDevicesLoading, setMicDevicesLoading] = useState(false);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const recordingTimeoutRef = useRef<number | null>(null);

  const RECORDING_MAX_MS = 60_000;

  function clearRecordingTimeout() {
    if (recordingTimeoutRef.current !== null) {
      window.clearTimeout(recordingTimeoutRef.current);
      recordingTimeoutRef.current = null;
    }
  }

  function stopRecording() {
    clearRecordingTimeout();
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
    }
    setRecording(false);
  }

  const mobileShell = isCapacitorMobileBuild();
  const detectedLanguage = resolveLiveInputLanguage(inputText, explanationLanguage);
  const directionLabel = liveDirectionLabel(detectedLanguage, explanationLanguage, explanationLanguage);

  useEffect(() => {
    setNativeShell(isNativePlatform());
  }, []);

  const refreshMicDevices = useCallback(async (requestPermission: boolean) => {
    if (mobileShell || !navigator.mediaDevices?.enumerateDevices) {
      return;
    }
    setMicDevicesLoading(true);
    try {
      if (requestPermission) {
        await requestMicPermission();
      }
      const devices = await listAudioInputDevices();
      setMicDevices(devices);
      const stored = getStoredMicDeviceId();
      const preferred =
        stored && devices.some((device) => device.deviceId === stored)
          ? stored
          : devices[0]?.deviceId ?? "";
      setSelectedMicId((current) =>
        current && devices.some((device) => device.deviceId === current) ? current : preferred,
      );
    } catch {
      // Permission denied or no devices — selector stays hidden.
    } finally {
      setMicDevicesLoading(false);
    }
  }, [mobileShell]);

  useEffect(() => {
    if (mobileShell) {
      return;
    }
    void refreshMicDevices(false);
  }, [mobileShell, refreshMicDevices]);

  useEffect(() => {
    return () => {
      if (recordingTimeoutRef.current !== null) {
        window.clearTimeout(recordingTimeoutRef.current);
        recordingTimeoutRef.current = null;
      }
      mediaStreamRef.current?.getTracks().forEach((track) => track.stop());
    };
  }, []);

  function handleMicDeviceChange(deviceId: string) {
    setSelectedMicId(deviceId);
    if (deviceId) {
      storeMicDeviceId(deviceId);
    }
  }

  async function translateText(text: string, languageOverride?: LiveInputLanguage) {
    const trimmed = clampTranslationText(text.trim());
    if (!trimmed) {
      return;
    }

    const language = languageOverride ?? resolveLiveInputLanguage(trimmed, explanationLanguage);
    const direction = liveDirectionForLanguage(language);

    setInputText(trimmed);
    setLoading(true);
    setError(null);
    setOutput(null);
    setCopied(false);

    try {
      if (direction === "to_explanation") {
        const result = await understandIncomingText({
          source_text: trimmed,
          source_language: "es",
          target_language: explanationLanguage,
          locale_variant: "es-UY-montevideo",
          channel: "in_person",
        });
        const translated =
          explanationLanguage === "en"
            ? result.translation_en?.trim() || result.translation_ru?.trim() || ""
            : result.translation_ru?.trim() || result.translation_en?.trim() || "";
        if (!translated) {
          setError(t.errTranslationFailed);
          return;
        }
        setOutput({
          text: translated,
          direction,
          sourceLanguage: language,
          sourceText: trimmed,
        });
        return;
      }

      const result = await translateToEsuy({
        source_language: language === "ru" ? "ru" : "en",
        source_text: trimmed,
        context: {
          target_locale: "es-UY-montevideo",
          channel: "in_person",
        },
      });
      const spanish = result.recommended_reply?.trim() || "";
      if (!spanish) {
        setError(t.errTranslationFailed);
        return;
      }
      // Guard: never show a Russian paraphrase as the "Spanish" Live Chat result.
      if (language === "ru" && looksLikeRussian(spanish)) {
        setError(t.errTranslationFailed);
        return;
      }
      setOutput({
        text: spanish,
        direction,
        sourceLanguage: language,
        sourceText: trimmed,
      });
    } catch (translateError) {
      const message = translateError instanceof Error ? translateError.message : "Translation failed";
      setError(message === "Failed to fetch" ? t.errCannotReach : message);
    } finally {
      setLoading(false);
    }
  }

  async function translateFromAudio(file: File) {
    setLoading(true);
    setError(null);
    setOutput(null);
    setCopied(false);

    try {
      // Equal peers within the UI language pair (ru|es or en|es) — no forced home-language retry.
      const result = await transcribeAudio(
        file,
        liveSttLanguageHint(explanationLanguage),
        "in_person",
      );
      const transcript = clampTranslationText(result.transcript?.trim() ?? "");
      if (!transcript) {
        setError(t.errAudioTranslate);
        return;
      }
      setInputText(transcript);

      const normalizedLanguage = resolveLiveInputLanguage(
        transcript,
        explanationLanguage,
        result.language,
      );
      await translateText(transcript, normalizedLanguage);
    } catch (audioError) {
      const message = audioError instanceof Error ? audioError.message : "Audio translation failed";
      setError(message === "Failed to fetch" ? t.errCannotReach : message);
      setLoading(false);
    }
  }

  async function toggleRecording() {
    if (loading) {
      return;
    }

    if (recording) {
      stopRecording();
      return;
    }

    if (!navigator.mediaDevices?.getUserMedia) {
      setError(t.errMicUnavailable);
      return;
    }

    setError(null);
    try {
      if (!micDevices.length) {
        await refreshMicDevices(true);
      }
      const stream = await navigator.mediaDevices.getUserMedia(
        buildMicConstraints(selectedMicId || null),
      );
      mediaStreamRef.current = stream;
      audioChunksRef.current = [];

      const recorder = new MediaRecorder(stream);
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };
      recorder.onstop = () => {
        clearRecordingTimeout();
        stream.getTracks().forEach((track) => track.stop());
        mediaStreamRef.current = null;
        const blob = new Blob(audioChunksRef.current, {
          type: recorder.mimeType || "audio/webm",
        });
        const file = new File([blob], "live-recording.webm", { type: blob.type });
        void translateFromAudio(file);
      };

      mediaRecorderRef.current = recorder;
      recorder.start();
      setRecording(true);
      clearRecordingTimeout();
      recordingTimeoutRef.current = window.setTimeout(() => {
        recordingTimeoutRef.current = null;
        stopRecording();
      }, RECORDING_MAX_MS);
    } catch (micError) {
      clearRecordingTimeout();
      const message = micError instanceof Error ? micError.message : "";
      const denied =
        /permission|denied|NotAllowedError|NotReadableError/i.test(message) ||
        message.trim() === "";
      setError(denied ? t.errMicDenied : message || t.errMicDenied);
    }
  }

  async function copyOutput() {
    if (!output?.text) {
      return;
    }
    await navigator.clipboard.writeText(output.text);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  }

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    void translateText(inputText);
  }

  return (
    <main className="page page-live">
      <AppNav variant={mobileShell ? "compact" : "full"} />
      <QuickReplyApiHint error={error} />
      {error ? <p className="error quick-reply-banner-error">{error}</p> : null}

      <section className="hero">
        <p className="eyebrow">{t.liveTitle}</p>
        {!mobileShell ? <p className="lead">{t.liveLead}</p> : null}
      </section>

      <section className="card live-panel">
        <div className="live-mic-area">
          <button
            type="button"
            className={`live-mic-button ${recording ? "live-mic-button-active" : ""}`}
            onClick={() => void toggleRecording()}
            disabled={loading}
            aria-label={recording ? t.liveStop : t.liveMic}
          >
            {recording ? t.liveStop : loading ? "…" : t.liveMic}
          </button>
          <p className="muted live-mic-hint">
            {recording ? t.liveRecording : t.liveTapSpeak}
          </p>
          {!mobileShell ? (
            <div className="live-mic-device">
              <label className="field-label" htmlFor="live-mic-device">
                {t.liveMicrophone}
              </label>
              <div className="live-mic-device-row">
                <select
                  id="live-mic-device"
                  className="select"
                  value={selectedMicId}
                  disabled={recording || micDevicesLoading}
                  onChange={(event) => handleMicDeviceChange(event.target.value)}
                >
                  {micDevices.length === 0 ? (
                    <option value="">{t.liveDefaultMic}</option>
                  ) : (
                    micDevices.map((device) => (
                      <option key={device.deviceId} value={device.deviceId}>
                        {device.label}
                      </option>
                    ))
                  )}
                </select>
                <button
                  type="button"
                  className="button secondary small"
                  disabled={recording || micDevicesLoading}
                  onClick={() => void refreshMicDevices(true)}
                >
                  {micDevicesLoading ? "…" : t.liveRefresh}
                </button>
              </div>
              {micDevices.length === 0 ? (
                <p className="muted live-mic-device-hint">{t.liveMicHint}</p>
              ) : null}
            </div>
          ) : null}
        </div>

        <form className="live-text-fallback" onSubmit={handleSubmit}>
          <textarea
            id="live-text"
            className="textarea"
            rows={3}
            value={inputText}
            maxLength={MAX_TRANSLATION_CHARS}
            onChange={(event) => setInputText(clampTranslationText(event.target.value))}
            placeholder={t.livePlaceholder}
            aria-label={t.liveTypeLabel}
          />
          <p className="muted">{formatCharCount(t.charCountLabel, inputText.length, MAX_TRANSLATION_CHARS)}</p>

          {inputText.trim() ? (
            <p className="live-direction-badge">{directionLabel}</p>
          ) : null}

          <button
            type="submit"
            className="button primary"
            disabled={loading || !inputText.trim()}
          >
            {loading ? t.liveTranslating : t.liveTranslate}
          </button>
        </form>
      </section>

      {output ? (
        <section className="card live-output">
          <div className="reply-block">
            <div className="reply-header">
              <h3>{t.liveOutput}</h3>
              <div className="reply-actions">
                {output.direction === "to_es" ? <AudioPlayer key={output.text} text={output.text} /> : null}
                {nativeShell ? (
                  <button
                    type="button"
                    className="button primary small"
                    onClick={() => void shareReplyText(output.text, t.liveShare)}
                  >
                    {t.liveShare}
                  </button>
                ) : (
                  <button type="button" className="button primary small" onClick={() => void copyOutput()}>
                    {copied ? t.liveCopied : t.liveCopy}
                  </button>
                )}
                {output.direction === "to_es" ? (
                  <AddToVocabButton
                    spanishText={output.text}
                    sourceLanguage={output.sourceLanguage}
                    sourceOriginalText={output.sourceText}
                  />
                ) : null}
              </div>
            </div>
            <p className="reply-text live-output-text">{output.text}</p>
          </div>
          <TranslationRatingControl
            feature="live_chat"
            sourceText={output.sourceText}
            resultText={output.text}
            direction={output.direction}
          />
        </section>
      ) : null}
    </main>
  );
}
