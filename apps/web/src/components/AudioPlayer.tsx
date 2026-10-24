"use client";

import { useEffect, useRef, useState } from "react";

import { useAppLanguage } from "@/components/AppLanguageProvider";
import { fetchMediaBlob, synthesizeAudio } from "@/lib/api";
import { resolveMediaUrl } from "@/lib/api-config";

interface AudioPlayerProps {
  text: string;
  label?: string;
}

function revokeBlobUrl(url: string | null) {
  if (url?.startsWith("blob:")) {
    URL.revokeObjectURL(url);
  }
}

export function AudioPlayer({ text, label }: AudioPlayerProps) {
  const { t } = useAppLanguage();
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    setAudioUrl((current) => {
      revokeBlobUrl(current);
      return null;
    });
    setError(null);
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.removeAttribute("src");
      audioRef.current.load();
    }
  }, [text]);

  useEffect(() => {
    return () => {
      revokeBlobUrl(audioUrl);
    };
  }, [audioUrl]);

  async function loadAndPlay() {
    const trimmed = text.trim();
    if (!trimmed) {
      setError("Nothing to speak");
      return;
    }

    if (audioUrl) {
      try {
        const el = audioRef.current ?? new Audio(audioUrl);
        el.src = audioUrl;
        await el.play();
      } catch (playError) {
        const message = playError instanceof Error ? playError.message : "Audio failed";
        setError(message);
      }
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const result = await synthesizeAudio(trimmed);
      const mediaUrl = resolveMediaUrl(result.audio_url);
      if (!mediaUrl) {
        throw new Error("Audio URL is empty");
      }

      const blob = await fetchMediaBlob(mediaUrl);
      if (!blob.size) {
        throw new Error("Empty audio file");
      }
      const blobUrl = URL.createObjectURL(blob);

      setAudioUrl((current) => {
        revokeBlobUrl(current);
        return blobUrl;
      });

      // Play via a dedicated element — avoid a visible <audio controls> that
      // surfaces WebView "no supported source" when MIME was wrong.
      let el = audioRef.current;
      if (!el) {
        el = new Audio();
        audioRef.current = el;
      }
      el.src = blobUrl;
      await el.play();
    } catch (playError) {
      setAudioUrl((current) => {
        revokeBlobUrl(current);
        return null;
      });
      const message =
        playError instanceof Error ? playError.message : "Audio failed";
      setError(
        message === "Failed to fetch" ||
          message.startsWith("Failed to fetch (API:") ||
          /timeout|timed out|NetworkError/i.test(message)
          ? t.errCannotReach
          : /Voice synthesis|озвучк|TTS|temporarily unavailable/i.test(message)
            ? t.errTtsUnavailable
            : message.includes("no supported source") || message.includes("NotSupportedError")
              ? t.errAudioTranslate
              : message,
      );
    } finally {
      setLoading(false);
    }
  }

  const actionLabel = audioUrl ? t.playAudio : (label ?? t.speak);

  return (
    <div className="audio-player">
      <div className="audio-player-actions">
        <button
          type="button"
          className="button secondary small"
          onClick={() => void loadAndPlay()}
          disabled={loading || !text.trim()}
        >
          {loading ? t.generatingAudio : actionLabel}
        </button>
      </div>
      {error ? <p className="error">{error}</p> : null}
    </div>
  );
}
