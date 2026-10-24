from decime_api.schemas.compose import ReplyBundle, TranslateToEsRequest
from decime_api.schemas.incoming import UnderstandTextRequest, UnderstandTextResponse
from decime_api.services.compose.dialect_stamp import build_dialect_stamp


class FakeLLMProvider:
    provider_name = "fake"
    model_name = "fake-compose-v1"

    def __init__(self) -> None:
        self.last_usage: dict | None = None

    def _set_fake_usage(self) -> None:
        from decime_api.services.analytics.llm_usage import usage_snapshot

        self.last_usage = usage_snapshot(
            model=self.model_name,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
        )

    async def translate_to_esuy(self, request: TranslateToEsRequest) -> ReplyBundle:
        self._set_fake_usage()
        text = request.source_text.lower()
        dialect_stamp = build_dialect_stamp(request.context)
        simple_level = request.context.user_level == "A2"

        if "карт" in text or "card" in text or "tarjeta" in text:
            recommended = (
                "Hola, ¿se puede pagar con tarjeta?"
                if simple_level
                else "Hola, quería consultar si se puede pagar con tarjeta."
            )
            return ReplyBundle(
                target_locale=request.context.target_locale,
                dialect_stamp=dialect_stamp,
                source_language=_detect_language(request.source_language, text),
                intent_summary_ru="Пользователь хочет вежливо уточнить, можно ли оплатить картой.",
                intent_summary_en="The user wants to politely ask if card payment is accepted.",
                recommended_reply=recommended,
            )

        if "отправ" in text or "send" in text or "mando" in text or "счёт" in text or "счет" in text:
            recommended = (
                "Sí, ahora te mando la factura."
                if simple_level
                else "Sí, te mando la factura en un ratito."
            )
            return ReplyBundle(
                target_locale=request.context.target_locale,
                dialect_stamp=dialect_stamp,
                source_language=_detect_language(request.source_language, request.source_text),
                intent_summary_ru="Пользователь хочет сказать, что сейчас отправит счёт.",
                intent_summary_en="The user wants to say they will send the invoice now.",
                recommended_reply=recommended,
            )

        recommended = (
            "Hola, ¿me podés ayudar con eso?"
            if simple_level
            else "Hola, quería consultar sobre eso."
        )
        return ReplyBundle(
            target_locale=request.context.target_locale,
            dialect_stamp=dialect_stamp,
            source_language=_detect_language(request.source_language, text),
            intent_summary_ru=f"Пользователь хочет сказать: {request.source_text[:120]}",
            intent_summary_en=f"The user wants to say: {request.source_text[:120]}",
            recommended_reply=recommended,
            warnings=["fake_provider_response"],
        )

    async def understand_incoming(self, request: UnderstandTextRequest) -> UnderstandTextResponse:
        self._set_fake_usage()
        text = request.source_text.strip()
        lower = text.lower()
        translation_ru = "Демо-перевод входящего сообщения."
        translation_en = "Demo translation of the incoming message."

        if "podés" in lower and "10" in lower:
            translation_ru = "Ты можешь зайти завтра после 10?"
            translation_en = "Can you come tomorrow after 10?"
        elif "factura" in lower or "mandar" in lower:
            translation_ru = "Можешь отправить мне счёт?"
            translation_en = "Can you send me the invoice?"
        elif "tarjeta" in lower or "pagar" in lower:
            translation_ru = "Можно оплатить картой?"
            translation_en = "Can I pay by card?"

        return UnderstandTextResponse(
            original_text=text,
            translation_ru=translation_ru,
            translation_en=translation_en,
            tone_notes_ru=[],
            uncertain_parts=[],
            detected_locale=request.locale_variant,
        )


def _detect_language(source_language: str, text: str) -> str:
    if source_language != "auto":
        return source_language
    if any("\u0400" <= char <= "\u04FF" for char in text):
        return "ru"
    if any(word in text.lower() for word in ("the", "please", "can", "want", "how")):
        return "en"
    return "es"
