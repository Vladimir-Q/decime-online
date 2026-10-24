from decime_api.schemas.compose import Channel, ReplyContext

CHANNEL_LABELS: dict[Channel, str] = {
    "whatsapp_text": "WhatsApp",
    "in_person": "In person",
}


def build_dialect_stamp(context: ReplyContext) -> str:
    channel = CHANNEL_LABELS.get(context.channel, context.channel)
    level = context.user_level or "any"
    return f"🇺🇾 Uruguay · Montevideo · {channel} · {level}-friendly"
