"""Small reply catalogue for the v0.1.0 bilingual interface."""

from __future__ import annotations

from typing import Final

DEFAULT_LANGUAGE: Final = "zh"

MESSAGES: Final[dict[str, dict[str, str]]] = {
    "zh": {
        "ready": "松鼠小貓已經醒來了！",
        "missing_target": "請選擇一位成員或一個身分組作為提醒對象。",
        "too_many_targets": "一次提醒只能選擇一位成員或一個身分組。",
        "everyone_denied": "只有擁有「提及 @everyone、@here 和所有身分組」權限的人，才能設定 @everyone 提醒。",
        "amount_required": "選擇「X 分鐘後」、「X 小時後」或「每 X 小時」時，請填入大於 0 的數字。",
        "amount_not_needed": "只有選擇「X 分鐘後」、「X 小時後」或「每 X 小時」時才需要填寫數值。",
        "preview_title": "提醒設定預覽",
        "preview_notice": "v0.1.0 目前只會驗證並預覽設定，還不會真的送出提醒。",
        "field_message": "提醒內容",
        "field_type": "提醒種類",
        "field_target": "提醒對象",
        "field_interval": "間隔",
        "in_minutes": "{amount} 分鐘後（一次）",
        "in_hours": "{amount} 小時後（一次）",
        "every_hours": "每 {amount} 小時",
        "type_once": "一次",
        "type_in_minutes": "X 分鐘後（一次）",
        "type_in_hours": "X 小時後（一次）",
        "type_daily": "每天",
        "type_weekly": "每星期",
        "type_monthly": "每月",
        "type_every_hours": "每 X 小時",
    },
    "en": {
        "ready": "Squicat is awake!",
        "missing_target": "Choose one member or one role as the reminder target.",
        "too_many_targets": "Each reminder can target only one member or one role.",
        "everyone_denied": "Only members with Discord's Mention @everyone, @here, and All Roles permission may set an @everyone reminder.",
        "amount_required": "For in X minutes, in X hours, or every X hours, enter a number greater than 0.",
        "amount_not_needed": "Amount is only used with in X minutes, in X hours, or every X hours.",
        "preview_title": "Reminder preview",
        "preview_notice": "v0.1.0 validates and previews this setup only; it will not send a real reminder yet.",
        "field_message": "Message",
        "field_type": "Reminder type",
        "field_target": "Target",
        "field_interval": "Interval",
        "in_minutes": "In {amount} minutes (once)",
        "in_hours": "In {amount} hours (once)",
        "every_hours": "Every {amount} hours",
        "type_once": "Once",
        "type_in_minutes": "In X minutes (once)",
        "type_in_hours": "In X hours (once)",
        "type_daily": "Daily",
        "type_weekly": "Weekly",
        "type_monthly": "Monthly",
        "type_every_hours": "Every X hours",
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
