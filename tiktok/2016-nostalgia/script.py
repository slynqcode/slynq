"""Сценарий ролика «2026 — это новый 2016» (TikTok, 9:16). Озвучка — бесплатный Piper, голос Ирина."""

NARRATOR = "irina"

SEGMENTS = [
    {"id": "hook", "voice": NARRATOR,
     "text": "Весь Тикток сейчас пишет: двадцать шестой — это новый шестнадцатый. Давай вспомним, каким был тот год."},
    {"id": "filter", "voice": NARRATOR,
     "text": "Все снимали сторис с собачьим фильтром и радугой изо рта."},
    {"id": "mannequin", "voice": NARRATOR,
     "text": "Мы замирали в манекен-челлендже, а камера медленно ехала по комнате."},
    {"id": "hunt", "voice": NARRATOR,
     "text": "Гуляли по городу до ночи, чтобы поймать редкого монстрика в телефоне."},
    {"id": "battery", "voice": NARRATOR,
     "text": "Телефон садился к обеду, а пауэрбанк весил как кирпич."},
    {"id": "today", "voice": NARRATOR,
     "text": "Сейчас у нас вроде бы есть всё. Но почему-то так хочется обратно."},
    {"id": "cta", "voice": NARRATOR,
     "text": "А что помнишь ты из шестнадцатого? Пиши в комментариях."},
]

GAP = 0.3  # пауза между репликами, сек

EDGE_VOICES = {NARRATOR: {"voice": "ru-RU-SvetlanaNeural", "rate": "+5%", "pitch": "+0Hz"}}
PIPER_VOICES = {NARRATOR: {"model": "ru_RU-irina-medium", "length_scale": 0.92}}

# ElevenLabs (встроенный голос, доступен на бесплатном тарифе)
ELEVEN_VOICES = {NARRATOR: {"voice_id": "cgSgspJ2msm6clMCkdW9", "stability": 0.4, "style": 0.4}}  # Jessica
