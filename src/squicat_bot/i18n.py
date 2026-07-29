"""Small reply catalogue for the v0.1.0 bilingual interface."""

from __future__ import annotations

from typing import Final

DEFAULT_LANGUAGE: Final = "zh"

MESSAGES: Final[dict[str, dict[str, str]]] = {
    "zh": {
        "ready": "松鼠小貓已經醒來了！",
        "missing_target": "未選擇提醒對象時，會預設提醒你自己。",
        "too_many_targets": "一次提醒只能選擇一位成員或一個身分組。",
        "everyone_denied": "只有擁有「提及 @everyone、@here 和所有身分組」權限的人，才能設定 @everyone 提醒。",
        "schedule_required": "請在「一次」、「每 X 小時」、「每 X 天」或「每 X 個月」中填寫一項。",
        "only_one_schedule": "一次提醒只能填寫一種時間／重複方式。",
        "invalid_once_duration": "「一次」請填寫小時和／或分鐘，例如 5h30m、2h 或 30m。",
        "preview_title": "提醒設定預覽",
        "preview_notice": "v0.1.0 目前只會驗證並預覽設定，還不會真的送出提醒。",
        "field_message": "提醒內容",
        "field_type": "提醒種類",
        "field_target": "提醒對象",
        "field_interval": "間隔",
        "once_after": "{duration} 後（一次）",
        "every_hours": "每 {amount} 小時",
        "every_days": "每 {amount} 天",
        "every_months": "每 {amount} 個月",
        "type_once": "一次",
        "type_every_hours": "每 X 小時",
        "type_every_days": "每 X 天",
        "type_every_months": "每 X 個月",
    },
    "en": {
        "ready": "Squicat is awake!",
        "missing_target": "When no target is selected, the reminder defaults to you.",
        "too_many_targets": "Each reminder can target only one member or one role.",
        "everyone_denied": "Only members with Discord's Mention @everyone, @here, and All Roles permission may set an @everyone reminder.",
        "schedule_required": "Fill in one of: once, every X hours, every X days, or every X months.",
        "only_one_schedule": "Each reminder can use only one timing or repeat option.",
        "invalid_once_duration": "For once, enter hours and/or minutes, for example 5h30m, 2h, or 30m.",
        "preview_title": "Reminder preview",
        "preview_notice": "v0.1.0 validates and previews this setup only; it will not send a real reminder yet.",
        "field_message": "Message",
        "field_type": "Reminder type",
        "field_target": "Target",
        "field_interval": "Interval",
        "once_after": "In {duration} (once)",
        "every_hours": "Every {amount} hours",
        "every_days": "Every {amount} days",
        "every_months": "Every {amount} months",
        "type_once": "Once",
        "type_every_hours": "Every X hours",
        "type_every_days": "Every X days",
        "type_every_months": "Every X months",
    },
}


def language_for(locale: object, fallback: str = DEFAULT_LANGUAGE) -> str:
    """Map a Discord locale (or config value) to a supported catalogue language."""
    value = str(locale).lower()
    if value.startswith("en"):
        return "en"
    if value.startswith("zh"):
        return "zh"
    return "en" if fallback.lower().startswith("en") else "zh"


def text(language: str, key: str, **values: object) -> str:
    """Return a translated message with optional named substitutions."""
    return MESSAGES[language][key].format(**values)
