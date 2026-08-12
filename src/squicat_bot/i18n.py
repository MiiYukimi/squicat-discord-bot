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
        "schedule_required": "請填寫「一次」、「指定時間」或一種重複方式。",
        "only_one_schedule": "「一次」或重複方式只能選一種；「指定時間」可搭配重複方式，作為第一次觸發時間。",
        "invalid_once_duration": "「一次」請填寫小時和／或分鐘，例如 5h30m、2h 或 30m。",
        "invalid_specific_time": "「指定時間」請填寫尚未過去的時間：今天 1730、明天 1500，或 YYYYMMDD HHMM（例如 20260731 1500）。時間以馬來西亞時間計算。",
        "scheduled_title": "提醒已建立",
        "scheduled_notice": "松鼠小貓會在時間到時，於這個頻道送出提醒。",
        "delivery_title": "提醒時間到！",
        "delivery_footer": "由 {creator} 設定的提醒",
        "delivery_unavailable": "原本的提醒對象已無法使用，因此沒有標註任何人。",
        "field_message": "提醒內容",
        "field_type": "提醒種類",
        "field_target": "提醒對象",
        "field_interval": "間隔",
        "field_channel": "發佈頻道",
        "field_first_run": "第一次觸發",
        "channel_unavailable": "松鼠小貓無法在這個頻道發送訊息；請確認 Bot 擁有「查看頻道」和「傳送訊息」權限。",
        "once_after": "{duration} 後（一次）",
        "once_at": "{time}（一次）",
        "every_hours": "每 {amount} 小時",
        "every_days": "每 {amount} 天",
        "every_months": "每 {amount} 個月",
        "type_once": "一次",
        "type_every_hours": "每 X 小時",
        "type_every_days": "每 X 天",
        "type_every_months": "每 X 個月",
        "list_title": "你的進行中提醒",
        "list_empty": "你目前沒有進行中或排程中的提醒。",
        "list_footer": "一次提醒觸發後會自動從這裡移除。重複提醒可使用 /停止提醒 的編號停止。",
        "list_item": "**#{id}** · {message}\n還有 **{remaining}** 觸發 · {schedule}\n對象：{target} · 發佈：{channel}",
        "cancelled_title": "重複提醒已停止",
        "cancelled_message": "已停止 #{id}：{message}",
        "cancel_not_found": "找不到這個提醒編號，或它不是你建立的提醒。",
        "cancel_once": "#{id} 是一次性提醒，觸發後會自動刪除，不需要停止循環。",
        "voice_modal_title": "① 讓松鼠小貓說什麼？",
        "voice_message_label": "訊息內容",
        "voice_message_placeholder": "輸入松鼠小貓要發出的訊息",
        "voice_empty": "訊息不能是空的喔。",
        "voice_channel_step": "② 選擇松鼠小貓要發言的頻道",
        "voice_channel_placeholder": "選擇目標頻道",
        "voice_owner_only": "這個指令只有松鼠小貓的擁有者可以使用。",
        "voice_sent": "已由松鼠小貓發送到 {channel}。",
        "voice_send_failed": "松鼠小貓暫時無法發送這則訊息，請再試一次。",
    },
    "en": {
        "ready": "Squicat is awake!",
        "missing_target": "When no target is selected, the reminder defaults to you.",
        "too_many_targets": "Each reminder can target only one member or one role.",
        "everyone_denied": "Only members with Discord's Mention @everyone, @here, and All Roles permission may set an @everyone reminder.",
        "schedule_required": "Fill in once, at time, or one repeat option.",
        "only_one_schedule": "Choose only one of once or the repeat options. At time can be combined with a repeat option as the first delivery time.",
        "invalid_once_duration": "For once, enter hours and/or minutes, for example 5h30m, 2h, or 30m.",
        "invalid_specific_time": "For at time, enter a future time: today 1730, tomorrow 1500, or YYYYMMDD HHMM (for example 20260731 1500). Times use Malaysia time.",
        "scheduled_title": "Reminder scheduled",
        "scheduled_notice": "Squicat will send the reminder in this channel when it is due.",
        "delivery_title": "Reminder time!",
        "delivery_footer": "Set by {creator}",
        "delivery_unavailable": "The original target is no longer available, so no one was mentioned.",
        "field_message": "Message",
        "field_type": "Reminder type",
        "field_target": "Target",
        "field_interval": "Interval",
        "field_channel": "Posting channel",
        "field_first_run": "First delivery",
        "channel_unavailable": "Squicat cannot send messages in that channel. Check that it has View Channel and Send Messages permissions.",
        "once_after": "In {duration} (once)",
        "once_at": "At {time} (once)",
        "every_hours": "Every {amount} hours",
        "every_days": "Every {amount} days",
        "every_months": "Every {amount} months",
        "type_once": "Once",
        "type_every_hours": "Every X hours",
        "type_every_days": "Every X days",
        "type_every_months": "Every X months",
        "list_title": "Your active reminders",
        "list_empty": "You have no active or scheduled reminders.",
        "list_footer": "One-time reminders disappear after delivery. Stop a repeating reminder with its ID using /stop_reminder.",
        "list_item": "**#{id}** · {message}\nDue in **{remaining}** · {schedule}\nTarget: {target} · Posts in: {channel}",
        "cancelled_title": "Repeating reminder stopped",
        "cancelled_message": "Stopped #{id}: {message}",
        "cancel_not_found": "That reminder ID was not found, or it was not created by you.",
        "cancel_once": "#{id} is a one-time reminder. It deletes itself after delivery, so it does not need to be stopped.",
        "voice_modal_title": "1. What should Squicat say?",
        "voice_message_label": "Message",
        "voice_message_placeholder": "Write the message Squicat should post",
        "voice_empty": "The message cannot be empty.",
        "voice_channel_step": "2. Choose where Squicat should speak",
        "voice_channel_placeholder": "Choose a target channel",
        "voice_owner_only": "Only Squicat's application owner can use this command.",
        "voice_sent": "Squicat posted the message in {channel}.",
        "voice_send_failed": "Squicat could not send that message right now. Please try again.",
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
