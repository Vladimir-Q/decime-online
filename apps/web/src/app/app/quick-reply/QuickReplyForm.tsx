"use client";

import { useEffect, useRef, useState } from "react";

import { AppNav } from "@/components/AppNav";
import { useAppLanguage } from "@/components/AppLanguageProvider";
import { QuickReplyApiHint } from "@/components/QuickReplyApiHint";
import { UserLevelSelector } from "@/features/compose/UserLevelSelector";
import { ReplyBundleCard } from "@/features/compose/ReplyBundleCard";
import { TranslationRatingControl } from "@/features/feedback/TranslationRatingControl";
import { translateToEsuy, transcribeAudio, understandIncomingText } from "@/lib/api";
import { readClipboardAudioFile, readClipboardText } from "@/lib/clipboard";
import { isCapacitorMobileBuild } from "@/lib/capacitor-build";
import { syncDecimeE2E } from "@/lib/capacitor-e2e";
import { capacitorUriToPath, guessMimeType } from "@/lib/native-audio-upload";
import { consumePendingShareAudioUri, consumePendingShareError, consumePendingShareText, clearForceQuickReply } from "@/lib/native-share";
import { isRetryableTranslateError, sanitizeSharedText, waitForShareTranslateReady } from "@/lib/share-text";
import { clampTranslationText, MAX_TRANSLATION_CHARS } from "@/lib/translation-limits";
import type { TranslateToEsResponse, ReplyContext } from "@/types/compose";
import type { TargetExplanationLanguage, UnderstandTextResponse } from "@/types/incoming";

function formatCharCount(template: string, current: number, max: number): string {
  return template.replace("{current}", String(current)).replace("{max}", String(max));
}

const defaultContext: ReplyContext = {
  target_locale: "es-UY-montevideo",
  channel: "whatsapp_text",
  user_level: null,
};

function pickTranslation(
  understanding: UnderstandTextResponse,
  language: TargetExplanationLanguage,
): string | null {
  const ru = understanding.translation_ru?.trim() || null;
  const en = understanding.translation_en?.trim() || null;
  if (language === "en") {
    return en || ru;
  }
  return ru || en;
}

export function QuickReplyForm() {
  const { language: explanationLanguage, t } = useAppLanguage();
  const audioInputRef = useRef<HTMLInputElement>(null);
  const [incomingText, setIncomingText] = useState("");
  const [userReply, setUserReply] = useState("");
  const [context, setContext] = useState<ReplyContext>(defaultContext);
  const [understanding, setUnderstanding] = useState<UnderstandTextResponse | null>(null);
  const [reply, setReply] = useState<TranslateToEsResponse | null>(null);
  const [understandLoading, setUnderstandLoading] = useState(false);
  const [replyLoading, setReplyLoading] = useState(false);
  const [audioLoading, setAudioLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function consumeNativeSharePayload() {
    await clearForceQuickReply();

    const pendingError = await consumePendingShareError();
    if (pendingError) {
      setError(pendingError);
    }

    const pendingText = await consumePendingShareText();
    if (pendingText) {
      const clean = sanitizeSharedText(pendingText);
      if (!clean) {
        return;
      }
      setIncomingText(clean);
      setUnderstanding(null);
      setReply(null);
      await waitForShareTranslateReady();
      void understandText(clean, explanationLanguage, { fromShare: true });
      return;
    }

    const audioUri = await consumePendingShareAudioUri();
    if (!audioUri) {
      return;
    }

    setAudioLoading(true);
    setError(null);
    try {
      const filePath = capacitorUriToPath(audioUri);
      const fileName = filePath?.split(/[/\\]/).pop() ?? "shared-audio.ogg";
      const mimeType = guessMimeType(fileName);
      const placeholder = new File([], fileName, { type: mimeType });
      const result = await transcribeAudio(placeholder, "es", "whatsapp_audio", { filePath });
      const transcript = clampTranslationText(result.transcript?.trim() ?? "");
      if (!transcript) {
        setError(t.errTranscribeEmpty);
        return;
      }
      setIncomingText(transcript);
      setUnderstanding(null);
      setReply(null);
      void understandText(transcript);
    } catch (shareAudioError) {
      const message =
        shareAudioError instanceof Error ? shareAudioError.message : "Could not transcribe shared audio";
      setError(
        message.includes("Transcribe failed") || message.includes("Network")
          ? t.errCannotReach
          : message,
      );
    } finally {
      setAudioLoading(false);
    }
  }

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const incoming = clampTranslationText(params.get("incoming")?.trim() ?? "");
    if (incoming) {
      setIncomingText(incoming);
      void understandText(incoming);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    void consumeNativeSharePayload();
  }, []);

  useEffect(() => {
    async function runE2EAction(action: string, payload?: string | null) {
      if (action === "translate") {
        await handleUnderstand();
        return;
      }
      if (action === "paste") {
        await handlePasteIncoming();
        return;
      }
      if (action === "generate" && payload) {
        await generateReply(payload);
      }
    }

    async function runPendingE2EAction() {
      if (!isCapacitorMobileBuild()) {
        return;
      }
      const { Preferences } = await import("@capacitor/preferences");
      const { value } = await Preferences.get({ key: "decime_e2e_action" });
      if (!value) {
        return;
      }
      await Preferences.remove({ key: "decime_e2e_action" });
      await runE2EAction(value);
    }

    void runPendingE2EAction();

    const onE2EAction = (event: Event) => {
      const detail = (event as CustomEvent<{ action?: string; payload?: string | null }>).detail;
      if (detail?.action) {
        void runE2EAction(detail.action, detail.payload);
      }
    };

    window.addEventListener("decime-e2e-action", onE2EAction);
    return () => window.removeEventListener("decime-e2e-action", onE2EAction);
  }, [incomingText]);

  useEffect(() => {
    const onNativeShare = () => {
      void consumeNativeSharePayload();
    };

    window.addEventListener("decime-share-updated", onNativeShare);
    return () => window.removeEventListener("decime-share-updated", onNativeShare);
  }, []);

  useEffect(() => {
    const trimmed = incomingText.trim();
    if (!trimmed || !understanding) {
      return;
    }
    void understandText(trimmed, explanationLanguage);
    // Re-translate when app language changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [explanationLanguage]);

  async function handlePasteIncoming() {
    setError(null);
    try {
      if (isCapacitorMobileBuild()) {
        const { Preferences } = await import("@capacitor/preferences");
        const { value: injected } = await Preferences.get({ key: "decime_e2e_paste_text" });
        if (injected?.trim()) {
          await Preferences.remove({ key: "decime_e2e_paste_text" });
          const pasted = clampTranslationText(injected.trim());
          setIncomingText(pasted);
          setUnderstanding(null);
          setReply(null);
          void understandText(pasted);
          return;
        }
      }

      const clipboard = await readClipboardText();
      if (!clipboard) {
        setError(t.errClipboardEmpty);
        return;
      }
      const text = clampTranslationText(clipboard);
      if (!text) {
        setError(t.errClipboardEmpty);
        return;
      }
      setIncomingText(text);
      setUnderstanding(null);
      setReply(null);
      void understandText(text);
    } catch (pasteError) {
      const message = pasteError instanceof Error ? pasteError.message : "";
      setError(
        /permission|denied|NotAllowedError/i.test(message)
          ? t.errClipboardDenied
          : message || t.errClipboardDenied,
      );
    }
  }

  async function handlePasteAudio() {
    setError(null);
    setAudioLoading(true);
    try {
      const file = await readClipboardAudioFile();
      if (!file) {
        setError(t.errNoAudioClipboard);
        return;
      }
      await transcribeIncomingFile(file);
    } catch (pasteError) {
      const message = pasteError instanceof Error ? pasteError.message : "";
      setError(
        /permission|denied|NotAllowedError|not available/i.test(message)
          ? t.errNoAudioClipboard
          : message || t.errNoAudioClipboard,
      );
    } finally {
      setAudioLoading(false);
    }
  }

  async function transcribeIncomingFile(file: File) {
    setAudioLoading(true);
    setError(null);
    try {
      const result = await transcribeAudio(file, "es", "whatsapp_audio");
      const transcript = clampTranslationText(result.transcript?.trim() ?? "");
      if (!transcript) {
        setError(t.errTranscribeEmpty);
        return;
      }
      setIncomingText(transcript);
      setUnderstanding(null);
      setReply(null);
      void understandText(transcript);
    } catch (transcribeError) {
      setError(transcribeError instanceof Error ? transcribeError.message : "Transcribe failed");
    } finally {
      setAudioLoading(false);
    }
  }

  async function understandText(
    text: string,
    language: TargetExplanationLanguage = explanationLanguage,
    options?: { fromShare?: boolean },
  ) {
    if (understandLoading) {
      return;
    }

    const trimmed = clampTranslationText(sanitizeSharedText(text));
    if (!trimmed) {
      return;
    }
    setIncomingText(trimmed);
    setUnderstandLoading(true);
    setError(null);
    setReply(null);

    const maxAttempts = options?.fromShare ? 2 : 1;
    let lastMessage = "Understand failed";

    try {
      for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
        try {
          if (options?.fromShare && attempt > 0) {
            await waitForShareTranslateReady(4_000);
          }
          const result = await understandIncomingText({
            source_text: trimmed,
            source_language: "es",
            target_language: language,
            locale_variant: context.target_locale,
            channel: context.channel,
          });
          setUnderstanding(result);
          const picked = pickTranslation(result, language);
          if (!picked?.trim()) {
            setError(t.errTranslationFailed);
          }
          return;
        } catch (understandError) {
          lastMessage =
            understandError instanceof Error ? understandError.message : "Understand failed";
          if (attempt + 1 < maxAttempts && isRetryableTranslateError(lastMessage)) {
            await new Promise((resolve) => window.setTimeout(resolve, 1_200));
            continue;
          }
          throw understandError;
        }
      }
    } catch (understandError) {
      const message =
        understandError instanceof Error ? understandError.message : lastMessage;
      if (isRetryableTranslateError(message)) {
        setError(t.errTranslateBusy);
      } else {
        setError(message === "Failed to fetch" ? t.errCannotReach : message);
      }
    } finally {
      setUnderstandLoading(false);
    }
  }

  async function handleUnderstand() {
    await understandText(incomingText);
  }

  async function generateReply(intentOverride?: string) {
    if (replyLoading) {
      return;
    }

    const intent = clampTranslationText((intentOverride ?? userReply).trim());
    if (!intent) {
      return;
    }

    setUserReply(intent);

    setReplyLoading(true);
    setError(null);
    try {
      const result = await translateToEsuy({
        source_language: explanationLanguage,
        source_text: intent,
        context,
      });
      setReply(result);
    } catch (generateError) {
      const message =
        generateError instanceof Error ? generateError.message : "Generate failed";
      setError(
        message === "Failed to fetch" ? t.errCannotReach : message,
      );
    } finally {
      setReplyLoading(false);
    }
  }

  function handleGenerateReplySubmit(event: React.FormEvent) {
    event.preventDefault();
    void generateReply();
  }

  const translation =
    understanding ? pickTranslation(understanding, explanationLanguage) : null;

  useEffect(() => {
    syncDecimeE2E(
      {
        incomingText,
        userReply,
        error,
        audioLoading,
        understandLoading,
        replyLoading,
        translation,
        replySpanish: reply?.recommended_reply?.trim() ?? null,
      },
      {
        translate: handleUnderstand,
        generate: (intent) => generateReply(intent),
        pasteText: handlePasteIncoming,
      },
    );
  }, [
    incomingText,
    userReply,
    error,
    audioLoading,
    understandLoading,
    replyLoading,
    translation,
    reply,
  ]);

  const mobileShell = isCapacitorMobileBuild();

  return (
    <main className="page page-quick-reply">
      <AppNav variant={mobileShell ? "compact" : "full"} />
      <QuickReplyApiHint error={error} />
      {error ? <p className="error quick-reply-banner-error">{error}</p> : null}
      <section className="hero">
        <p className="eyebrow">{t.qrTitle}</p>
        {!mobileShell ? <p className="lead">{t.qrLead}</p> : null}
      </section>

      <section className="card quick-reply-section">
        <div className="quick-reply-section-header">
          <h2>{t.qrStep1}</h2>
          <div className="quick-reply-actions">
            <button type="button" className="button secondary small" onClick={() => void handlePasteIncoming()}>
              {t.qrPasteText}
            </button>
            <button
              type="button"
              className="button secondary small"
              onClick={() => void handlePasteAudio()}
              disabled={audioLoading}
            >
              {audioLoading ? t.qrWorking : t.qrPasteAudio}
            </button>
            <button
              type="button"
              className="button secondary small"
              onClick={() => audioInputRef.current?.click()}
              disabled={audioLoading}
            >
              {t.qrUploadAudio}
            </button>
            <input
              ref={audioInputRef}
              type="file"
              accept="audio/*"
              hidden
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) {
                  void transcribeIncomingFile(file);
                }
                event.target.value = "";
              }}
            />
          </div>
        </div>

        <textarea
          id="incoming-text"
          className="textarea"
          rows={3}
          value={incomingText}
          maxLength={MAX_TRANSLATION_CHARS}
          onChange={(event) => {
            setIncomingText(clampTranslationText(event.target.value));
            setUnderstanding(null);
            setReply(null);
          }}
          placeholder={t.qrIncomingPlaceholder}
          aria-label={t.qrIncomingLabel}
        />
        <p className="muted">{formatCharCount(t.charCountLabel, incomingText.length, MAX_TRANSLATION_CHARS)}</p>

        <div className="quick-reply-inline">
          <button
            type="button"
            className="button primary"
            disabled={understandLoading || !incomingText.trim()}
            onClick={() => void handleUnderstand()}
          >
            {understandLoading ? t.qrTranslating : t.qrTranslate}
          </button>
        </div>

        {understandLoading ? <p className="muted">{t.qrCallingApi}</p> : null}

        {understanding ? (
          <div className="understanding-panel">
            <p className="understanding-label">{t.qrTranslation}</p>
            {translation ? (
              <p className="understanding-text">{translation}</p>
            ) : (
              <p className="muted">{t.qrTranslationEmpty}</p>
            )}
            {understanding.tone_notes_ru && understanding.tone_notes_ru.length > 0 ? (
              <p className="muted">
                {t.toneShort}: {understanding.tone_notes_ru.join(" · ")}
              </p>
            ) : null}
            {understanding.uncertain_parts && understanding.uncertain_parts.length > 0 ? (
              <p className="muted">
                {t.uncertain}: {understanding.uncertain_parts.join(" · ")}
              </p>
            ) : null}
            {translation ? (
              <TranslationRatingControl
                feature="quick_reply"
                sourceText={incomingText}
                resultText={translation}
                direction="to_explanation"
              />
            ) : null}
          </div>
        ) : null}
      </section>

      <section className="card quick-reply-section">
        <h2>{t.qrStep2}</h2>
        <form className="compose-form" onSubmit={handleGenerateReplySubmit}>
          <textarea
            id="user-reply"
            className="textarea"
            rows={3}
            value={userReply}
            maxLength={MAX_TRANSLATION_CHARS}
            onChange={(event) => setUserReply(clampTranslationText(event.target.value))}
            placeholder={
              explanationLanguage === "en" ? t.qrReplyPlaceholderEn : t.qrReplyPlaceholderRu
            }
            required
          />
          <p className="muted">{formatCharCount(t.charCountLabel, userReply.length, MAX_TRANSLATION_CHARS)}</p>
          <UserLevelSelector
            value={context.user_level ?? null}
            onChange={(user_level) => setContext({ ...context, user_level })}
          />
          <button
            type="submit"
            className="button primary"
            disabled={replyLoading || !userReply.trim()}
            onClick={() => void generateReply()}
          >
            {replyLoading ? t.qrGenerating : t.qrGenerate}
          </button>
        </form>
      </section>

      {reply ? (
        <section className="card quick-reply-section">
          <h2>{t.qrStep3}</h2>
          <p className="muted">{t.qrStep3Hint}</p>
          <ReplyBundleCard
            reply={reply}
            sourceText={userReply}
            sourceLanguage={reply.source_language || explanationLanguage}
            copyPrimaryLabel={t.qrCopyWhatsApp}
            shareLabel={t.qrShareWhatsApp}
            hideIntentSummary
          />
        </section>
      ) : null}
    </main>
  );
}
