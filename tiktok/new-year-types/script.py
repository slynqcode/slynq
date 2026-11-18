"""Сценарий ролика «До Нового года 43 дня: 5 типов людей» (TikTok, 9:16). Озвучка — ElevenLabs."""

NARRATOR = "jessica"

SEGMENTS = [
    {"id": "hook", "voice": NARRATOR,
     "text": "До Нового года сорок три дня. Есть пять типов людей. Ты какой?"},
    {"id": "planner", "voice": NARRATOR,
     "text": "Первый — составил список подарков ещё в ноябре и уже всё купил."},
    {"id": "tree", "voice": NARRATOR,
     "text": "Второй — ставит ёлку в середине ноября и с утра до ночи слушает новогодние песни."},
    {"id": "rush", "voice": NARRATOR,
     "text": "Третий — бежит за подарками тридцать первого в одиннадцать вечера."},
    {"id": "newlife", "voice": NARRATOR,
     "text": "Четвёртый — обещает начать новую жизнь с первого января. Уже пятый год подряд."},
    {"id": "sleeper", "voice": NARRATOR,
     "text": "А пятый просто спит до третьего января."},
    {"id": "cta", "voice": NARRATOR,
     "text": "Отметь друга, который точно третий тип. И напиши, какой ты!"},
]

GAP = 0.3  # пауза между репликами, сек

# ElevenLabs (встроенный голос, доступен на бесплатном тарифе)
ELEVEN_VOICES = {NARRATOR: {"voice_id": "cgSgspJ2msm6clMCkdW9", "stability": 0.4, "style": 0.45}}  # Jessica
EDGE_VOICES = {NARRATOR: {"voice": "ru-RU-SvetlanaNeural", "rate": "+5%", "pitch": "+0Hz"}}
PIPER_VOICES = {NARRATOR: {"model": "ru_RU-irina-medium", "length_scale": 0.92}}
