"""Сценарий ролика «4 трюка Чёрной пятницы» (TikTok, 9:16).

Каждая реплика = отдельная сцена. Озвучка генерируется через Fish Audio (tts.py),
длительность сцен берётся из длительности озвучки.
"""

NARRATOR = "48ec28a45588422b977a86460c11977f"  # Fish Audio: «Энергичный Рассказчик»
SELLER = NARRATOR  # голос кота-продавца (можно заменить на другой reference_id)

SEGMENTS = [
    {"id": "hook", "voice": NARRATOR,
     "text": "Чёрная пятница уже через десять дней. Вот четыре трюка, которыми тебя точно попытаются обмануть."},
    {"id": "price", "voice": NARRATOR,
     "text": "Трюк первый. За неделю до распродажи цену поднимают в три раза, а потом дарят тебе скидку семьдесят процентов."},
    {"id": "timer", "voice": NARRATOR,
     "text": "Трюк второй. Таймер «осталось пять минут». Обнови страницу, и он начнётся заново."},
    {"id": "stock", "voice": NARRATOR,
     "text": "Трюк третий. «Остался последний товар». Последний уже третий месяц подряд."},
    {"id": "cart", "voice": NARRATOR,
     "text": "Трюк четвёртый. В каталоге цена одна, а в корзине внезапно появляются доставка, сервисный сбор и подписка, которую ты не заказывал."},
    {"id": "meme", "voice": SELLER, "edge": "seller",
     "text": "А продавец такой: зачем мне тебя обманывать?"},
    {"id": "cta", "voice": NARRATOR,
     "text": "Проверяй историю цен заранее и сохрани видео, чтобы не попасться."},
]

GAP = 0.25  # пауза между репликами, сек

# Бесплатная озвучка Microsoft Edge TTS (используется, если ENGINE=edge)
EDGE_VOICES = {
    NARRATOR: {"voice": "ru-RU-DmitryNeural", "rate": "+10%", "pitch": "+0Hz"},
    "seller": {"voice": "ru-RU-DmitryNeural", "rate": "-12%", "pitch": "-10Hz"},
}

# Запасной бесплатный офлайн-движок Piper (нейросеть, работает без интернета)
PIPER_VOICES = {
    NARRATOR: {"model": "ru_RU-ruslan-medium", "length_scale": 0.88},
    "seller": {"model": "ru_RU-denis-medium", "length_scale": 1.1},
}

# ElevenLabs (встроенные голоса, доступны на бесплатном тарифе)
ELEVEN_VOICES = {
    NARRATOR: {"voice_id": "TX3LPaxmHKxFdv7VdQ7I", "stability": 0.35, "style": 0.45},  # Liam — бодрый рассказчик
    "seller": {"voice_id": "JBFqnCBsd6RMkjVDRZzb", "stability": 0.45, "style": 0.6},   # George — хитрый продавец
}
