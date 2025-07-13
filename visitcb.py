"""
Visit Callback Notifier
Author: Sam & ChatGPT
Purpose: Automatically log in to Visit MIS (via HTTP Basic‑Auth),
         filter for “Recall” callbacks, find any due in the next N minutes,
         and post them in Discord via webhook.
         Now supports an optional MEMBER NAME column per MIS.
         Accepts command‑line args so Windows Task Scheduler can pass in
         “--future-min” and “--lookback-hrs” without editing the script.
"""

import os
import re
import json
import datetime
import requests
import pytz
import argparse
from playwright.sync_api import sync_playwright

# ─── DYNAMIC CONFIG LOAD ──────────────────────────────────────────────────────

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    cfg = json.load(f)

MASTER_SWITCH = cfg.get("master_switch", True)

MIS_SOURCES = []
for name, sys in cfg["systems"].items():
    MIS_SOURCES.append({
        "name":            name,
        "url":             sys["url"],
        "prop_id_col":     sys["prop_id_col"],
        "remarks_col":     sys["remarks_col"],
        "member_name_col": sys.get("member_name_col"),
        "filter_label":    sys["filter_label"],
        "icon":            sys.get("icon", "🔷"),
        "active":          sys.get("active", True),
    })

USERNAME    = os.getenv("MIS_USERNAME", "visit")
PASSWORD    = os.getenv("MIS_PASSWORD", "Visit@544")
WEBHOOK_URL = os.getenv(
    "DISCORD_WEBHOOK",
    "https://discordapp.com/api/webhooks/1392492996276125697/JghUPAs2h94WABtR4j_7rjegeRDcovA9jkH2xGrmHQ2fUWun5HZ9ld5HUtPwxDaGwt-H"
)

# ─── ARGUMENT PARSING ─────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(
        description="Visit Callback Notifier: ahead & look‑back window"
    )
    p.add_argument(
        "--future-min",
        type=int,
        default=int(os.getenv("FUTURE_MIN", 15)),
        help="minutes ahead to warn (default: env FUTURE_MIN or 15)",
    )
    p.add_argument(
        "--lookback-hrs",
        type=int,
        default=int(os.getenv("LOOKBACK_HOURS", 24)),
        help="hours behind to check missed (default: env LOOKBACK_HOURS or 24)",
    )
    return p.parse_args()

# ─── COOLDOWN HANDLING ─────────────────────────────────────────────────────────

COOLDOWN_FILE = os.path.join(os.path.dirname(__file__), "last_sent.txt")

def is_in_cooldown(cooldown_minutes: int) -> bool:
    if not os.path.exists(COOLDOWN_FILE):
        return False
    try:
        with open(COOLDOWN_FILE, "r") as f:
            last_str = f.read().strip()
            last_dt = datetime.datetime.strptime(last_str, "%Y-%m-%d %H:%M:%S")
            now = datetime.datetime.now()
            return (now - last_dt).total_seconds() < cooldown_minutes * 60
    except Exception:
        return False

# ─── HELPERS ───────────────────────────────────────────────────────────────────

def parse_datetime(text: str) -> datetime.datetime | None:
    text = text.replace("Call At ", "").strip()
    text = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", text, flags=re.IGNORECASE)
    try:
        dt = datetime.datetime.strptime(text, "%B %d %Y, %I:%M %p")
        return pytz.timezone("Asia/Kolkata").localize(dt)
    except Exception:
        return None

def notify_discord(message: str):
    if not WEBHOOK_URL:
        print("❌  No DISCORD_WEBHOOK set — aborting.")
        return
    requests.post(WEBHOOK_URL, json={"content": message})

    # Save the time of this message
    with open(COOLDOWN_FILE, "w") as f:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(now)

def fetch_callbacks(
    page,
    source_name,
    prop_id_col,
    remarks_col,
    filter_label,
    future_min,
    lookback_hrs,
    member_name_col=None,
):
    upcoming, missed = [], []

    print(f"▶️  Applying '{filter_label}' filter for {source_name}...")
    page.select_option('select', label=filter_label)
    page.click('button:has-text("Apply Filter")')
    page.wait_for_selector("table tbody tr")

    rows = page.query_selector_all("table tbody tr")
    print(f"🔍  {source_name}: Found {len(rows)} rows.")

    now  = datetime.datetime.now(pytz.timezone("Asia/Kolkata"))
    soon = now + datetime.timedelta(minutes=future_min)
    past = now - datetime.timedelta(hours=lookback_hrs)

    for r in rows:
        cells = r.query_selector_all("td")
        if len(cells) <= max(prop_id_col, remarks_col, member_name_col or 0):
            continue
        prop_id = cells[prop_id_col].inner_text().strip()
        remarks = cells[remarks_col].inner_text().strip()

        if member_name_col is not None:
            member_name = cells[member_name_col].inner_text().strip()
        else:
            member_name = None

        sched_dt = parse_datetime(remarks)
        if not sched_dt:
            continue

        if now <= sched_dt <= soon:
            upcoming.append((source_name, prop_id, member_name, remarks))
        elif past <= sched_dt < now:
            missed.append((source_name, prop_id, member_name, remarks))

    return upcoming, missed

# ─── MAIN FLOW ─────────────────────────────────────────────────────────────────

def run(future_min: int, lookback_hrs: int):
    # Master switch check
    if not MASTER_SWITCH:
        print("🔕  Master switch is OFF — exiting without notifications.")
        return

    # Cooldown check first to avoid unnecessary work
    cooldown_minutes = cfg.get("cooldown_minutes", 0)
    if is_in_cooldown(cooldown_minutes):
        print(f"⏳  Cooldown active ({cooldown_minutes} min) — skipping everything.")
        return

    upcoming_all, missed_all = [], []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            http_credentials={"username": USERNAME, "password": PASSWORD}
        )
        page = context.new_page()

        for source in MIS_SOURCES:
            if not source["active"]:
                continue

            page.goto(source["url"])
            page.wait_for_selector('select:has-text("Filter by status")')

            up, mi = fetch_callbacks(
                page,
                source["name"],
                source["prop_id_col"],
                source["remarks_col"],
                source["filter_label"],
                future_min,
                lookback_hrs,
                source.get("member_name_col"),
            )
            upcoming_all.extend(up)
            missed_all.extend(mi)

        browser.close()

    if upcoming_all or missed_all:
        lines = ["🔔 Callback Alerts", ""]

        if missed_all:
            lines.append(f" **{len(missed_all)} Missed:**")
            for src, pid, member, remarks in missed_all:
                icon = next(s["icon"] for s in MIS_SOURCES if s["name"] == src)
                member_part = f" – **{member}**" if member else ""
                lines.append(f"• [{src} {icon}] `{pid}`{member_part} – {remarks}")

        if missed_all and upcoming_all:
            lines.append("──────────────────────────────")

        if upcoming_all:
            lines.append(f" **{len(upcoming_all)} due in {future_min} min:**")
            for src, pid, member, remarks in upcoming_all:
                icon = next(s["icon"] for s in MIS_SOURCES if s["name"] == src)
                member_part = f" – **{member}**" if member else ""
                lines.append(f"• [{src} {icon}] `{pid}`{member_part} – {remarks}")

        notify_discord("\n".join(lines))
        print("✅  Notification sent.")
    else:
        print("ℹ️  Nothing to report.")

if __name__ == "__main__":
    opts = parse_args()
    run(opts.future_min, opts.lookback_hrs)