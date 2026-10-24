/** Max characters for user translation inputs and STT text sent to translate/understand. */
export const MAX_TRANSLATION_CHARS = 1500;

export function clampTranslationText(text: string): string {
  if (text.length <= MAX_TRANSLATION_CHARS) {
    return text;
  }
  return text.slice(0, MAX_TRANSLATION_CHARS);
}
