#!/usr/bin/env python3
"""
telegram_fetcher.py
Periodically run this script (e.g., via cron or a Windows Task Scheduler job)
to pull every new message sent to your Telegram bot – even while it was offline –
and store them, plus any attachments, in JSON.

Requirements
------------
pip install requests python-dotenv

Environment
-----------
Create a .env file (or set an OS variable) with
BOT_TOKEN=123456:ABCDEF...

Usage
-----
python telegram_fetcher.py
"""

import os
import json
import time
from pathlib import Path
from datetime import datetime, timezone
import requests
from dotenv import load_dotenv

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
load_dotenv()  # reads .env if present
BOT_TOKEN = os.getenv("BOT_TOKEN", "<PUT_YOUR_TOKEN_HERE>")
API_ROOT = f"https://api.telegram.org/bot{BOT_TOKEN}"
FILES_ROOT = f"https://api.telegram.org/file/bot{BOT_TOKEN}"

FOLDER = Path("telegram_logs")
OFFSET_FILE = FOLDER / Path("last_offset.txt")
JSON_FILE = FOLDER / Path("messages.json")
DOWNLOAD_DIR = FOLDER / Path("downloads")

POLL_TIMEOUT = 10  # seconds for long-polling
MAX_RETRIES = 3    # network retries per request

# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def api_get(method: str, params: dict | None = None) -> dict:
    """Call a Telegram Bot API method with basic retry logic."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = requests.get(f"{API_ROOT}/{method}", params=params, timeout=POLL_TIMEOUT + 5)
            r.raise_for_status()
            data = r.json()
            if not data.get("ok"):
                raise RuntimeError(data)
            return data["result"]
        except Exception as exc:
            if attempt == MAX_RETRIES:
                raise
            print(f"[warn] {method} failed ({exc}) – retry {attempt}/{MAX_RETRIES}")
            time.sleep(1)


def download_attachment(file_id: str, dest_dir: Path) -> str:
    """Download the file specified by file_id. Return local file path (str)."""
    file_info = api_get("getFile", {"file_id": file_id})
    file_path = file_info["file_path"]           # e.g. photos/file_42.jpg
    url = f"{FILES_ROOT}/{file_path}"
    dest_dir.mkdir(exist_ok=True)
    local_path = dest_dir / Path(file_path).name
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(local_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    return str(local_path)


def load_offset() -> int:
    """Read the last processed update_id (or 0)."""
    if OFFSET_FILE.exists():
        try:
            return int(OFFSET_FILE.read_text().strip())
        except ValueError:
            pass
    return 0


def save_offset(offset: int) -> None:
    OFFSET_FILE.write_text(str(offset))


def load_json() -> list:
    if JSON_FILE.exists():
        with open(JSON_FILE, "r", encoding="utf-8") as fh:
            return json.load(fh)
    return []


def save_json(data: list) -> None:
    with open(JSON_FILE, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)


def message_record(update: dict) -> dict:
    """Extract a tidy record from an update (message or channel_post)."""
    msg = update.get("message") or update.get("channel_post") or {}
    record = {
        "update_id": update["update_id"],
        "chat_id": msg.get("chat", {}).get("id"),
        "date_utc": datetime.utcfromtimestamp(msg.get("date", 0))
                    .replace(tzinfo=timezone.utc).isoformat(),
        "from": msg.get("from", {}),
        "type": "unknown",
        "text": msg.get("text"),
        "caption": msg.get("caption"),
        "attachments": []
    }

    # text / command
    if "text" in msg and not msg["text"].startswith("/"):
        record["type"] = "text"

    # photos (choose highest-resolution entry)
    if "photo" in msg:
        record["type"] = "photo"
        photo = msg["photo"][-1]          # largest
        local_file = download_attachment(photo["file_id"], DOWNLOAD_DIR)
        record["attachments"].append({
            "file_id": photo["file_id"],
            "width": photo["width"],
            "height": photo["height"],
            "size": photo.get("file_size"),
            "saved_as": local_file
        })

    # documents
    if "document" in msg:
        record["type"] = "document"
        doc = msg["document"]
        local_file = download_attachment(doc["file_id"], DOWNLOAD_DIR)
        record["attachments"].append({
            "file_id": doc["file_id"],
            "mime_type": doc.get("mime_type"),
            "file_name": doc.get("file_name"),
            "size": doc.get("file_size"),
            "saved_as": local_file
        })

    # audio / voice
    for k in ("audio", "voice"):
        if k in msg:
            record["type"] = k
            aud = msg[k]
            local_file = download_attachment(aud["file_id"], DOWNLOAD_DIR)
            record["attachments"].append({
                "file_id": aud["file_id"],
                "duration": aud.get("duration"),
                "mime_type": aud.get("mime_type"),
                "saved_as": local_file
            })

    # video
    if "video" in msg:
        record["type"] = "video"
        vid = msg["video"]
        local_file = download_attachment(vid["file_id"], DOWNLOAD_DIR)
        record["attachments"].append({
            "file_id": vid["file_id"],
            "width": vid["width"],
            "height": vid["height"],
            "duration": vid.get("duration"),
            "mime_type": vid.get("mime_type"),
            "size": vid.get("file_size"),
            "saved_as": local_file
        })

    # sticker
    if "sticker" in msg:
        record["type"] = "sticker"
        stk = msg["sticker"]
        local_file = download_attachment(stk["file_id"], DOWNLOAD_DIR)
        record["attachments"].append({
            "file_id": stk["file_id"],
            "width": stk["width"],
            "height": stk["height"],
            "emoji": stk.get("emoji"),
            "saved_as": local_file
        })

    return record


def retrive_messages(save_to_file=True):
    last_offset = load_offset()
    print(f"[info] last processed update_id = {last_offset}")

    updates = api_get(
        "getUpdates",
        {
            "offset": last_offset + 1,
            "timeout": POLL_TIMEOUT,   # enable long-poll
        },
    )

    if not updates:
        print("[info] No new messages.")
        return

    stored_messages = load_json()

    for upd in updates:
        rec = message_record(upd)
        stored_messages.append(rec)
        last_offset = max(last_offset, upd["update_id"])
        print(f"[saved] {rec['type']} from chat {rec['chat_id']} (update_id {upd['update_id']})")

    if save_to_file:
        save_json(stored_messages)
    save_offset(last_offset)
    print(f"[info] Stored {len(updates)} new messages. New offset = {last_offset}")

    return stored_messages


if __name__ == "__main__":
    retrive_messages()
