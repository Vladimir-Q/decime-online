"use client";

import { useEffect, useState } from "react";

import type { TranslateToEsResponse } from "@/types/compose";

import { AudioPlayer } from "@/components/AudioPlayer";
import { useAppLanguage } from "@/components/AppLanguageProvider";
import { AddToVocabButton } from "@/features/training/AddToVocabButton";
import { TranslationRatingControl } from "@/features/feedback/TranslationRatingControl";
import { isNativePlatform, shareReplyText } from "@/lib/native-share";

import { DialectStamp } from "./DialectStamp";

interface ReplyBundleCardProps {
  reply: TranslateToEsResponse;
  sourceText: string;
  sourceLanguage: string;
  copyPrimaryLabel?: string;
  hideIntentSummary?: boolean;
  shareLabel?: string;
  showRating?: boolean;
}

export function ReplyBundleCard({
  reply,
  sourceText,
  sourceLanguage,
  copyPrimaryLabel,
  hideIntentSummary = false,
  shareLabel,
  showRating = true,
}: ReplyBundleCardProps) {
  const { t } = useAppLanguage();
  const [copiedField, setCopiedField] = useState<string | null>(null);
  const [nativeShell, setNativeShell] = useState(false);
  const resolvedCopyLabel = copyPrimaryLabel ?? t.copy;
  const resolvedShareLabel = shareLabel ?? t.qrShareWhatsApp;

  useEffect(() => {
    setNativeShell(isNativePlatform());
  }, []);

  async function copyText(label: string, text: string) {
    await navigator.clipboard.writeText(text);
    setCopiedField(label);
    window.setTimeout(() => setCopiedField(null), 1500);
  }

  async function handleShare(text: string) {
    await shareReplyText(text, resolvedShareLabel);
  }

  return (
    <article className="reply-card">
      <DialectStamp stamp={reply.dialect_stamp} />

      <ReplyBlock
        label={t.replyResult}
        text={reply.recommended_reply}
        fieldKey="recommended"
        copyPrimaryLabel={resolvedCopyLabel}
        shareLabel={resolvedShareLabel}
        copiedLabel={t.copied}
        defaultCopyLabel={t.copy}
        nativeShell={nativeShell}
        copiedField={copiedField}
        onCopy={copyText}
        onShare={handleShare}
        sourceLanguage={reply.source_language || sourceLanguage}
        sourceText={sourceText}
      />

      {reply.intent_summary_ru && !hideIntentSummary ? (
        <div className="notes">
          <strong>{t.meaning}</strong>
          <p>{reply.intent_summary_ru}</p>
        </div>
      ) : null}

      {showRating && reply.recommended_reply ? (
        <TranslationRatingControl
          feature="quick_reply"
          sourceText={sourceText}
          resultText={reply.recommended_reply}
          direction="to_es"
        />
      ) : null}
    </article>
  );
}

function ReplyBlock({
  label,
  text,
  fieldKey,
  copyPrimaryLabel,
  shareLabel,
  copiedLabel,
  defaultCopyLabel,
  nativeShell,
  copiedField,
  onCopy,
  onShare,
  sourceLanguage,
  sourceText,
}: {
  label: string;
  text: string;
  fieldKey: string;
  copyPrimaryLabel: string;
  shareLabel: string;
  copiedLabel: string;
  defaultCopyLabel: string;
  nativeShell: boolean;
  copiedField: string | null;
  onCopy: (fieldKey: string, text: string) => void;
  onShare: (text: string) => Promise<void>;
  sourceLanguage: string;
  sourceText: string;
}) {
  const canAddToTraining = Boolean(text.trim());

  return (
    <div className="reply-block">
      <div className="reply-header">
        <h3>{label}</h3>
        <div className="reply-actions">
          <AudioPlayer key={text} text={text} />
          {nativeShell ? (
            <button
              type="button"
              className="button primary small"
              onClick={() => void onShare(text)}
            >
              {shareLabel}
            </button>
          ) : (
            <button
              type="button"
              className={`button small ${copyPrimaryLabel === defaultCopyLabel ? "secondary" : "primary"}`}
              onClick={() => onCopy(fieldKey, text)}
            >
              {copiedField === fieldKey ? copiedLabel : copyPrimaryLabel}
            </button>
          )}
          {canAddToTraining ? (
            <AddToVocabButton
              spanishText={text}
              sourceLanguage={sourceLanguage}
              sourceOriginalText={sourceText}
            />
          ) : null}
        </div>
      </div>
      <p className="reply-text">{text}</p>
    </div>
  );
}
