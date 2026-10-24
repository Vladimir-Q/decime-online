import type { AppLanguage, UserPublic } from "@/types/auth";

import { isCapacitorMobileBuild } from "@/lib/capacitor-build";
import { fetchCurrentUser, updateMyPreferences } from "@/lib/auth";

const LANGUAGE_KEY = "decime_app_language";

export type { AppLanguage };

export type UiStrings = {
  navQuickReply: string;
  navLiveChat: string;
  navTraining: string;
  navSettings: string;
  navAdminUsers: string;
  navAdminAi: string;
  navAdminUsage: string;
  chooseLanguageTitle: string;
  chooseLanguageLead: string;
  chooseRussian: string;
  chooseEnglish: string;
  languageLabel: string;
  saveLanguage: string;
  languageSaved: string;
  logout: string;
  settingsTitle: string;
  settingsLead: string;
  addToVocab: string;
  addingToVocab: string;
  addedToVocab: string;
  ratingLabel: string;
  ratingGood: string;
  ratingMixed: string;
  ratingBad: string;
  dictTab: string;
  historyTab: string;
  reviewTab: string;
  speak: string;
  speaking: string;
  delete: string;
  deleting: string;
  refresh: string;
  clearHistory: string;
  clearing: string;
  loading: string;
  trainingLead: string;
  dictEmpty: string;
  dictCount: string;
  dictExportSheets: string;
  dictImportSheets: string;
  dictExporting: string;
  dictImporting: string;
  dictJobRunning: string;
  dictJobCompleted: string;
  dictJobFailed: string;
  dictJobPartial: string;
  dictImportTitle: string;
  dictImportSpreadsheet: string;
  dictImportSheetName: string;
  dictImportSubmit: string;
  dictImportCancel: string;
  dictJobCreated: string;
  dictJobSkipped: string;
  dictJobErrors: string;
  reviewDue: string;
  reviewCaughtUpTitle: string;
  reviewCaughtUpLead: string;
  showAnswer: string;
  expected: string;
  gradeAgain: string;
  gradeHard: string;
  gradeGood: string;
  gradeEasy: string;
  qrTitle: string;
  qrLead: string;
  qrStep1: string;
  qrPasteText: string;
  qrPasteAudio: string;
  qrUploadAudio: string;
  qrWorking: string;
  qrIncomingLabel: string;
  qrIncomingPlaceholder: string;
  charCountLabel: string;
  qrTranslate: string;
  qrTranslating: string;
  qrCallingApi: string;
  qrTranslation: string;
  qrTranslationEmpty: string;
  qrStep2: string;
  qrStep2Hint: string;
  qrReplyPlaceholderRu: string;
  qrReplyPlaceholderEn: string;
  qrGenerate: string;
  qrGenerating: string;
  qrStep3: string;
  qrStep3Hint: string;
  qrCopyWhatsApp: string;
  qrShareWhatsApp: string;
  liveTitle: string;
  liveLead: string;
  liveMic: string;
  liveStop: string;
  liveRecording: string;
  liveTapSpeak: string;
  liveMicrophone: string;
  liveDefaultMic: string;
  liveRefresh: string;
  liveMicHint: string;
  liveTypeLabel: string;
  livePlaceholder: string;
  liveAppLanguage: string;
  liveTranslate: string;
  liveTranslating: string;
  liveOutput: string;
  liveCopy: string;
  liveCopied: string;
  liveShare: string;
  loginTitle: string;
  loginEmail: string;
  loginPassword: string;
  loginSubmit: string;
  loginBusy: string;
  loginRegister: string;
  loginSignIn: string;
  loginName: string;
  checkingSession: string;
  signInRequired: string;
  signInRequiredLead: string;
  logIn: string;
  recommended: string;
  simpler: string;
  shorter: string;
  moreFormal: string;
  notes: string;
  meaning: string;
  copy: string;
  copied: string;
  toneLabel: string;
  toneNeutral: string;
  toneFriendly: string;
  toneSimple: string;
  historyEmpty: string;
  playAudio: string;
  generatingAudio: string;
  regenerate: string;
  reviewDueNow: string;
  reviewInSession: string;
  reviewLoading: string;
  loginCreateAccount: string;
  loginNeedAccount: string;
  loginHaveAccount: string;
  loginOpenApp: string;
  liveDirEsRu: string;
  liveDirEsEn: string;
  liveDirRuEs: string;
  liveDirEnEs: string;
  uncertain: string;
  toneShort: string;
  listenRecall: string;
  stage: string;
    skippedDuplicates: string;
  adminHint: string;
  errCannotReach: string;
  errTtsUnavailable: string;
  errTranslationFailed: string;
  errTranslateBusy: string;
    errClipboardEmpty: string;
  errNoAudioClipboard: string;
  errClipboardDenied: string;
  errTranscribeEmpty: string;
  errMicUnavailable: string;
  errMicDenied: string;
  errAudioTranslate: string;
  landingEyebrow: string;
  landingTitle: string;
  landingLead: string;
  landingVersion: string;
  landingLogin: string;
  landingFaq: string;
  landingLangRu: string;
  landingLangEn: string;
  faqTitle: string;
  faqLead: string;
  faqBackHome: string;
  faqQ1: string;
  faqA1: string;
  faqQ2: string;
  faqA2: string;
  faqQ3: string;
  faqA3: string;
  faqQ4: string;
  faqA4: string;
  faqQ5: string;
  faqA5: string;
  toneRecommended: string;
  replyResult: string;
  footerFaq: string;
};

const STRINGS: Record<AppLanguage, UiStrings> = {
  ru: {
    navQuickReply: "Быстрый ответ",
    navLiveChat: "Живой чат",
    navTraining: "Тренировка",
    navSettings: "Настройки",
    navAdminUsers: "Пользователи",
    navAdminAi: "AI",
    navAdminUsage: "Статистика",
    chooseLanguageTitle: "Выберите язык",
    chooseLanguageLead:
      "Язык интерфейса и переводов с/на испанский. Можно изменить позже в настройках.",
    chooseRussian: "Русский",
    chooseEnglish: "English",
    languageLabel: "Язык приложения",
    saveLanguage: "Сохранить язык",
    languageSaved: "Язык: Русский",
    logout: "Выйти",
    settingsTitle: "Настройки",
    settingsLead: "Язык интерфейса и аккаунт.",
    addToVocab: "В словарь",
    addingToVocab: "Добавляю…",
    addedToVocab: "Добавлено",
    ratingLabel: "Оценка перевода",
    ratingGood: "Хорошо",
    ratingMixed: "Есть недочёты",
    ratingBad: "Плохо",
    dictTab: "Словарь",
    historyTab: "История",
    reviewTab: "Тренировка",
    speak: "Озвучить",
    speaking: "Озвучиваю…",
    delete: "Удалить",
    deleting: "Обновляю…",
    refresh: "Обновить",
    clearHistory: "Очистить историю",
    clearing: "Очищаю…",
    loading: "Загрузка…",
    trainingLead: "Словарь, история сообщений и тренировка в одном разделе.",
    dictEmpty: "Словарь пуст. Добавляйте фразы из Быстрого ответа или Живого чата.",
    dictCount: "записей",
    dictExportSheets: "Экспорт в Google Sheets",
    dictImportSheets: "Импорт из Google Sheets",
    dictExporting: "Экспорт…",
    dictImporting: "Импорт…",
    dictJobRunning: "Операция выполняется…",
    dictJobCompleted: "Готово",
    dictJobFailed: "Ошибка",
    dictJobPartial: "Завершено с ошибками по строкам",
    dictImportTitle: "Импорт словаря",
    dictImportSpreadsheet: "ID или URL таблицы Google Sheets",
    dictImportSheetName: "Имя вкладки",
    dictImportSubmit: "Запустить импорт",
    dictImportCancel: "Отмена",
    dictJobCreated: "создано",
    dictJobSkipped: "пропущено",
    dictJobErrors: "ошибок",
    reviewDue: "К повторению",
    reviewCaughtUpTitle: "Всё повторено",
    reviewCaughtUpLead: "Сейчас нет карточек к повторению. Вернитесь позже или добавьте новые.",
    showAnswer: "Показать ответ",
    expected: "Ожидается",
    gradeAgain: "Снова",
    gradeHard: "Сложно",
    gradeGood: "Хорошо",
    gradeEasy: "Легко",
    qrTitle: "Быстрый ответ",
    qrLead:
      "Вставьте входящее сообщение на испанском, чтобы увидеть перевод, или сразу напишите ответ на русском и получите испанский текст.",
    qrStep1: "Входящее сообщение (необязательно)",
    qrPasteText: "Вставить текст",
    qrPasteAudio: "Вставить аудио",
    qrUploadAudio: "Загрузить аудио",
    qrWorking: "Обработка…",
    qrIncomingLabel: "Испанский (из WhatsApp)",
    qrIncomingPlaceholder: "Вставьте полученное сообщение…",
    charCountLabel: "{current} / {max}",
    qrTranslate: "Перевести",
    qrTranslating: "Перевожу…",
    qrCallingApi: "Запрос перевода…",
    qrTranslation: "Перевод",
    qrTranslationEmpty: "Перевод пустой — нажмите «Перевести» ещё раз.",
    qrStep2: "Перевод вашего текста на испанский",
    qrStep2Hint: "Пишите по-русски, первый шаг можно пропустить, если нужен только ответ.",
    qrReplyPlaceholderRu: "Что хотите сказать по-русски…",
    qrReplyPlaceholderEn: "What you want to say in English…",
    qrGenerate: "Сделать ответ на испанском",
    qrGenerating: "Генерирую…",
    qrStep3: "Ответ на испанском",
    qrStep3Hint: "Скопируйте текст и вставьте в WhatsApp. Decime не отправляет сообщения сам.",
    qrCopyWhatsApp: "Копировать в WhatsApp",
    qrShareWhatsApp: "Поделиться в WhatsApp",
    liveTitle: "Живой чат",
    liveLead: "Говорите или печатайте. Направление перевода определяется автоматически.",
    liveMic: "Микрофон",
    liveStop: "Стоп",
    liveRecording: "Запись… нажмите, чтобы остановить",
    liveTapSpeak: "Нажмите, чтобы говорить",
    liveMicrophone: "Микрофон",
    liveDefaultMic: "Микрофон по умолчанию",
    liveRefresh: "Обновить",
    liveMicHint: "Нажмите «Обновить», чтобы разрешить доступ и увидеть устройства.",
    liveTypeLabel: "Или введите фразу",
    livePlaceholder: "Или введите фразу на испанском/русском",
    liveAppLanguage: "Язык приложения",
    liveTranslate: "Перевести",
    liveTranslating: "Перевожу…",
    liveOutput: "Перевод",
    liveCopy: "Копировать",
    liveCopied: "Скопировано",
    liveShare: "Поделиться",
    loginTitle: "Вход",
    loginEmail: "Email",
    loginPassword: "Пароль",
    loginSubmit: "Войти",
    loginBusy: "Вхожу…",
    loginRegister: "Регистрация",
    loginSignIn: "Вход",
    loginName: "Имя",
    checkingSession: "Проверка сессии…",
    signInRequired: "Нужен вход",
    signInRequiredLead: "Этот сервер требует авторизации.",
    logIn: "Войти",
    recommended: "Рекомендуемый",
    simpler: "Проще",
    shorter: "Короче",
    moreFormal: "Формальнее",
    notes: "Заметки",
    meaning: "Смысл",
    copy: "Копировать",
    copied: "Скопировано",
    toneLabel: "Вариант ответа",
    toneNeutral: "Нейтральный",
    toneFriendly: "Дружелюбный",
    toneSimple: "Простой (A2)",
    toneRecommended: "Рекомендуемый",
    replyResult: "Ответ",
    historyEmpty: "Пока нет запросов. Сгенерируйте ответ в Быстром ответе.",
    landingEyebrow: "Decime UY",
    landingTitle: "Приложение для перевода и изучения испанского языка",
    landingLead:
      "Понимайте, что вам отправляют в сообщениях, отвечайте на испанском и сохраняйте полезные фразы для тренировки.",
    landingVersion: "Версия",
    landingLogin: "Войти",
    landingFaq: "FAQ",
    landingLangRu: "Русский",
    landingLangEn: "English",
    faqTitle: "Частые вопросы",
    faqLead: "Кратко о том, как пользоваться Decime UY.",
    faqBackHome: "На главную",
    faqQ1: "Что такое Живой чат?",
    faqA1:
      "Режим для разговора лично: говорите или вводите текст, сервис переводит между испанским и вашим языком (русский или английский).",
    faqQ2: "Чем отличается Быстрый ответ?",
    faqA2:
      "Вставьте сообщение на испанском, чтобы увидеть перевод, или сразу напишите ответ на русском, чтобы получить его на испанском.",
    faqQ3: "Что такое Тренировка?",
    faqA3:
      "Ваш словарь живых фраз из реальных диалогов. Добавляйте выражения из ответов и повторяйте их с интервалами, чтобы они лучше запоминались.",
    faqQ4: "Как работает озвучка?",
    faqA4:
      "К испанским фразам можно сгенерировать аудио. Сейчас генерация может быть медленной или отключена (STT/TTS) — это нормально для текущей версии с локальными малыми моделями.",
    faqQ5: "Нужен ли аккаунт?",
    faqA5:
      "Да, для сохранения истории и словаря нужен вход. На главной нажмите «Войти» и используйте выданный логин.",
    playAudio: "Воспроизвести",
    generatingAudio: "Генерирую аудио…",
    regenerate: "Заново",
    reviewDueNow: "К повторению",
    reviewInSession: "В этой сессии",
    reviewLoading: "Загрузка очереди…",
    loginCreateAccount: "Создать аккаунт",
    loginNeedAccount: "Нет аккаунта? Регистрация",
    loginHaveAccount: "Уже есть аккаунт? Войти",
    loginOpenApp: "Открыть приложение",
    liveDirEsRu: "Испанский → русский",
    liveDirEsEn: "Испанский → английский",
    liveDirRuEs: "Русский → испанский (Уругвай)",
    liveDirEnEs: "Английский → испанский (Уругвай)",
    uncertain: "Неясно",
    toneShort: "Тон",
    listenRecall: "Послушайте и вспомните смысл.",
    stage: "Этап",
    skippedDuplicates: "пропущено дублей",
    adminHint: "Вход как",
    errCannotReach: "Нет связи с сервером. Проверьте интернет и попробуйте снова.",
    errTtsUnavailable: "Озвучка временно недоступна. Попробуйте чуть позже.",
    errTranslationFailed: "Не удалось перевести. Попробуйте ещё раз.",
    errTranslateBusy: "Сервис перевода занят. Нажмите «Перевести» ещё раз.",
    errClipboardEmpty: "Буфер обмена пуст. Сначала скопируйте сообщение из WhatsApp.",
    errNoAudioClipboard: "В буфере нет аудио. Сохраните голосовое и нажмите «Загрузить аудио».",
    errClipboardDenied: "Нет доступа к буферу. Скопируйте текст и нажмите «Вставить текст» ещё раз.",
    errTranscribeEmpty: "Распознавание вернуло пустой текст. Аудио слишком короткое или неразборчивое.",
    errMicUnavailable: "Микрофон недоступен в этом браузере. Введите текст.",
    errMicDenied: "Нет доступа к микрофону. Разрешите микрофон в настройках Android.",
    errAudioTranslate: "Не удалось распознать аудио. Попробуйте ещё раз или введите фразу.",
    footerFaq: "Помощь",
  },
  en: {
    navQuickReply: "Quick Reply",
    navLiveChat: "Live Chat",
    navTraining: "Training",
    navSettings: "Settings",
    navAdminUsers: "Users",
    navAdminAi: "AI",
    navAdminUsage: "Usage",
    chooseLanguageTitle: "Choose your language",
    chooseLanguageLead:
      "Sets the UI and Spanish translation direction. You can change this later in Settings.",
    chooseRussian: "Русский",
    chooseEnglish: "English",
    languageLabel: "App language",
    saveLanguage: "Save language",
    languageSaved: "Language: English",
    logout: "Log out",
    settingsTitle: "Settings",
    settingsLead: "App language and account.",
    addToVocab: "Add to vocab",
    addingToVocab: "Adding…",
    addedToVocab: "Added",
    ratingLabel: "Translation quality",
    ratingGood: "Good",
    ratingMixed: "Needs work",
    ratingBad: "Bad",
    dictTab: "Dictionary",
    historyTab: "History",
    reviewTab: "Review",
    speak: "Speak",
    speaking: "Speaking…",
    delete: "Delete",
    deleting: "Updating…",
    refresh: "Refresh",
    clearHistory: "Clear history",
    clearing: "Clearing…",
    loading: "Loading…",
    trainingLead: "Dictionary, message history, and spaced review in one place.",
    dictEmpty: "Dictionary is empty. Add phrases from Quick Reply or Live Chat.",
    dictCount: "item(s)",
    dictExportSheets: "Export to Google Sheets",
    dictImportSheets: "Import from Google Sheets",
    dictExporting: "Exporting…",
    dictImporting: "Importing…",
    dictJobRunning: "Working…",
    dictJobCompleted: "Done",
    dictJobFailed: "Failed",
    dictJobPartial: "Finished with row errors",
    dictImportTitle: "Import dictionary",
    dictImportSpreadsheet: "Google Sheets ID or URL",
    dictImportSheetName: "Sheet name",
    dictImportSubmit: "Start import",
    dictImportCancel: "Cancel",
    dictJobCreated: "created",
    dictJobSkipped: "skipped",
    dictJobErrors: "errors",
    reviewDue: "Due now",
    reviewCaughtUpTitle: "All caught up",
    reviewCaughtUpLead: "No items are due right now. Come back later or add more.",
    showAnswer: "Show answer",
    expected: "Expected",
    gradeAgain: "Again",
    gradeHard: "Hard",
    gradeGood: "Good",
    gradeEasy: "Easy",
    qrTitle: "Quick Reply",
    qrLead:
      "Paste an incoming Spanish message to see a translation, or write your reply in English right away and get Spanish text.",
    qrStep1: "Incoming message (optional)",
    qrPasteText: "Paste text",
    qrPasteAudio: "Paste audio",
    qrUploadAudio: "Upload audio",
    qrWorking: "Working…",
    qrIncomingLabel: "Spanish (from WhatsApp)",
    qrIncomingPlaceholder: "Paste the message you received…",
    charCountLabel: "{current} / {max}",
    qrTranslate: "Translate",
    qrTranslating: "Translating…",
    qrCallingApi: "Requesting translation…",
    qrTranslation: "Translation",
    qrTranslationEmpty: "Translation is empty — tap Translate again.",
    qrStep2: "Translate your text into Spanish",
    qrStep2Hint: "Write in English — you can skip the first step if you only need a reply.",
    qrReplyPlaceholderRu: "Что хотите сказать по-русски…",
    qrReplyPlaceholderEn: "What you want to say in English…",
    qrGenerate: "Make a Spanish reply",
    qrGenerating: "Generating…",
    qrStep3: "Spanish reply",
    qrStep3Hint: "Copy the text and paste it into WhatsApp. Decime does not send messages itself.",
    qrCopyWhatsApp: "Copy for WhatsApp",
    qrShareWhatsApp: "Share to WhatsApp",
    liveTitle: "Live Chat",
    liveLead: "Speak or type. Translation direction is detected automatically.",
    liveMic: "Mic",
    liveStop: "Stop",
    liveRecording: "Recording… tap to stop",
    liveTapSpeak: "Tap to speak",
    liveMicrophone: "Microphone",
    liveDefaultMic: "Default microphone",
    liveRefresh: "Refresh",
    liveMicHint: "Tap Refresh to allow microphone access and list devices.",
    liveTypeLabel: "Or type a phrase",
    livePlaceholder: "Or type a phrase in Spanish/Russian/English",
    liveAppLanguage: "App language",
    liveTranslate: "Translate",
    liveTranslating: "Translating…",
    liveOutput: "Translation",
    liveCopy: "Copy",
    liveCopied: "Copied",
    liveShare: "Share",
    loginTitle: "Sign in",
    loginEmail: "Email",
    loginPassword: "Password",
    loginSubmit: "Log in",
    loginBusy: "Signing in…",
    loginRegister: "Register",
    loginSignIn: "Sign in",
    loginName: "Display name",
    checkingSession: "Checking session…",
    signInRequired: "Sign in required",
    signInRequiredLead: "This server requires authentication.",
    logIn: "Log in",
    recommended: "Recommended",
    simpler: "Simpler",
    shorter: "Shorter",
    moreFormal: "More formal",
    notes: "Notes",
    meaning: "Meaning",
    copy: "Copy",
    copied: "Copied",
    toneLabel: "Reply style",
    toneNeutral: "Neutral",
    toneFriendly: "Friendly",
    toneSimple: "Simple (A2)",
    toneRecommended: "Recommended",
    replyResult: "Reply",
    historyEmpty: "No requests yet. Generate a reply in Quick Reply.",
    landingEyebrow: "Decime UY",
    landingTitle: "An app for translating and learning Spanish",
    landingLead:
      "Understand what people send you, reply in Spanish, and save useful phrases for practice.",
    landingVersion: "Version",
    landingLogin: "Log in",
    landingFaq: "FAQ",
    landingLangRu: "Русский",
    landingLangEn: "English",
    faqTitle: "FAQ",
    faqLead: "A short guide to using Decime UY.",
    faqBackHome: "Back to home",
    faqQ1: "What is Live Chat?",
    faqA1:
      "In-person mode: speak or type, and the service translates between Spanish and your language (Russian or English).",
    faqQ2: "How is Quick Reply different?",
    faqA2:
      "Paste a Spanish message to see a translation, or write your reply in English right away to get it in Spanish.",
    faqQ3: "What is Training?",
    faqA3:
      "Your dictionary of real phrases from conversations. Add expressions from replies and review them with spaced repetition so they stick better.",
    faqQ4: "How does audio work?",
    faqA4:
      "You can generate speech for Spanish phrases. Right now generation may be slow or unavailable (STT/TTS) — expected in this version with small local models.",
    faqQ5: "Do I need an account?",
    faqA5:
      "Yes — sign in to keep history and vocabulary. Use Log in on the home page with the credentials you were given.",
    playAudio: "Play",
    generatingAudio: "Generating audio…",
    regenerate: "Regenerate",
    reviewDueNow: "Due now",
    reviewInSession: "In this session",
    reviewLoading: "Loading review queue…",
    loginCreateAccount: "Create account",
    loginNeedAccount: "Need an account? Register",
    loginHaveAccount: "Already have an account? Sign in",
    loginOpenApp: "Open app",
    liveDirEsRu: "Spanish → Russian",
    liveDirEsEn: "Spanish → English",
    liveDirRuEs: "Russian → Spanish (Uruguay)",
    liveDirEnEs: "English → Spanish (Uruguay)",
    uncertain: "Uncertain",
    toneShort: "Tone",
    listenRecall: "Listen and recall the meaning.",
    stage: "Stage",
    skippedDuplicates: "skipped duplicates",
    adminHint: "Signed in as",
    errCannotReach: "Cannot reach the server. Check your connection and try again.",
    errTtsUnavailable: "Voice synthesis is temporarily unavailable. Please try again shortly.",
    errTranslationFailed: "Translation failed. Try again.",
    errTranslateBusy: "Translation service is busy. Tap Translate to retry.",
    errClipboardEmpty: "Clipboard is empty. Copy a WhatsApp message first.",
    errNoAudioClipboard: "No audio in clipboard. Save the voice note, then use Upload audio.",
    errClipboardDenied: "Clipboard access denied. Copy the text, then tap Paste text again.",
    errTranscribeEmpty: "Transcription returned empty. The audio may be too short or unreadable.",
    errMicUnavailable: "Microphone is not available in this browser. Use text input.",
    errMicDenied: "Microphone access denied. Allow the mic in Android settings.",
    errAudioTranslate: "Could not transcribe audio. Try again or type the phrase.",
    footerFaq: "Help",
  },
};

export function ui(language: AppLanguage): UiStrings {
  return STRINGS[language];
}

export async function getCachedAppLanguage(): Promise<AppLanguage | null> {
  if (typeof window === "undefined") {
    return null;
  }
  if (isCapacitorMobileBuild()) {
    try {
      const { Preferences } = await import("@capacitor/preferences");
      const { value } = await Preferences.get({ key: LANGUAGE_KEY });
      if (value === "ru" || value === "en") {
        return value;
      }
    } catch {
      // fall through
    }
  }
  const local = localStorage.getItem(LANGUAGE_KEY);
  return local === "ru" || local === "en" ? local : null;
}

export async function setCachedAppLanguage(language: AppLanguage): Promise<void> {
  if (typeof window === "undefined") {
    return;
  }
  localStorage.setItem(LANGUAGE_KEY, language);
  if (isCapacitorMobileBuild()) {
    try {
      const { Preferences } = await import("@capacitor/preferences");
      await Preferences.set({ key: LANGUAGE_KEY, value: language });
    } catch {
      // ignore
    }
  }
}

export async function resolveAppLanguage(user?: UserPublic | null): Promise<AppLanguage | null> {
  if (user?.app_language === "ru" || user?.app_language === "en") {
    await setCachedAppLanguage(user.app_language);
    return user.app_language;
  }
  return getCachedAppLanguage();
}

export async function saveAppLanguage(language: AppLanguage): Promise<UserPublic | null> {
  await setCachedAppLanguage(language);
  try {
    return await updateMyPreferences({ app_language: language });
  } catch {
    return null;
  }
}

export async function syncAppLanguageFromServer(): Promise<AppLanguage | null> {
  try {
    const me = await fetchCurrentUser();
    return resolveAppLanguage(me);
  } catch {
    return getCachedAppLanguage();
  }
}
