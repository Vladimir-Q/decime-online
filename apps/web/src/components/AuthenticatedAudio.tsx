"use client";

import { useEffect, useRef, useState } from "react";

import { useAppLanguage } from "@/components/AppLanguageProvider";
import { fetchMediaBlob } from "@/lib/api";
import { resolveMediaUrl } from "@/lib/api-config";

interface AuthenticatedAudioProps {
  url: string;
  className?: string;
}

function revokeBlobUrl(url: string | null) {
  if (url?.startsWith("blob:")) {
    URL.revokeObjectURL(url);
  }
}

export function AuthenticatedAudio({ url, className }: AuthenticatedAudioProps) {
  const { t } = useAppLanguage();
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    let cancelled = false;
    let objectUrl: string | null = null;

    async function load() {
      setLoading(true);
      setError(null);
      setBlobUrl((current) => {
        revokeBlobUrl(current);
        return null;
      });

      const mediaUrl = resolveMediaUrl(url);
      if (!mediaUrl) {
        setError("Audio URL is empty");
        setLoading(false);
        return;
      }

      try {
        const blob = await fetchMediaBlob(mediaUrl);
        if (cancelled) {
          return;
        }
        if (!blob.size) {
          throw new Error("Empty audio file");
        }
        objectUrl = URL.createObjectURL(blob);
        setBlobUrl(objectUrl);
      } catch (loadError) {
        if (!cancelled) {
          const message =
            loadError instanceof Error ? loadError.message : "Audio failed";
          setError(
            message === "Failed to fetch" ||
              message.startsWith("Failed to fetch (API:") ||
              /timeout|timed out|NetworkError/i.test(message)
              ? t.errCannotReach
              : message,
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void load();

    return () => {
      cancelled = true;
      revokeBlobUrl(objectUrl);
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.removeAttribute("src");
      }
    };
  }, [url, t.errCannotReach]);

  async function handlePlay() {
    if (!blobUrl) {
      return;
    }
    setError(null);
    try {
      let el = audioRef.current;
      if (!el) {
        el = new Audio();
        audioRef.current = el;
      }
      if (!el.paused && el.src === blobUrl) {
        el.pause();
        return;
      }
      el.src = blobUrl;
      await el.play();
    } catch (playError) {
      const message = playError instanceof Error ? playError.message : "Audio failed";
      setError(
        message.includes("no supported source") || message.includes("NotSupportedError")
          ? t.errAudioTranslate
          : message,
      );
    }
  }

  if (error) {
    return <p className={`error ${className ?? ""}`.trim()}>{error}</p>;
  }
  if (loading || !blobUrl) {
    return <p className={`muted ${className ?? ""}`.trim()}>{t.loading}</p>;
  }

  return (
    <div className={`authenticated-audio ${className ?? ""}`.trim()}>
      <button
        type="button"
        className="button secondary small"
        onClick={() => void handlePlay()}
      >
        {t.playAudio}
      </button>
    </div>
  );
}
