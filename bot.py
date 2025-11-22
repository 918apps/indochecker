# bot.py — FINAL VERSION (loads ALL txt files from Skiddle-ID/blocklist)
import requests
import sqlite3
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = "YOUR_BOT_TOKEN_HERE"                    # ← Change only this line
REPO_RAW = "https://raw.githubusercontent.com/Skiddle-ID/blocklist/main/"
LIST_URL = "https://api.github.com/repos/Skiddle-ID/blocklist/contents/"

# =================================== DATABASE ===================================
conn = sqlite3.connect("domains.db", check_same_thread=False)
c = conn.cursor()
c.execute("""CREATE TABLE IF NOT EXISTS domains (
                chat_id INTEGER,
                domain TEXT,
                last_status TEXT DEFAULT "unknown",
                PRIMARY KEY (chat_id, domain)
             )""")
c.execute("CREATE TABLE IF NOT EXISTS settings (chat_id INTEGER PRIMARY KEY, paused INTEGER DEFAULT 0)")
conn.commit()

# =================================== BLOCKLIST CACHE ===================================
blocked_set = set()

def refresh_full_blocklist():
    """Downloads the file list from GitHub and loads every .txt file"""
    global blocked_set
    new_set = set()
    try:
        # Get list of all files in the repo
        r = requests.get(LIST_URL, timeout=15)
        r.raise_for_status()
        files = r.json()

        for file in files:
            name = file["name"]
            if name.endswith(".txt") and not name.startswith("."):
                url = REPO_RAW + name
                print(f"Loading {name} ...")
                try:
                    txt = requests.get(url, timeout=20).text
                    for line in txt.splitlines():
                        line = line.strip().lower()
                        if line and not line.startswith("#"):
                            new_set.add(line)
                except:
                    continue

        blocked_set = new_set
        print(f"Blocklist fully refreshed → {len(blocked_set):,} entries from all .txt files")
    except Exception as e:
        print("Refresh failed:", e)

# First load
refresh_full_blocklist()

# =================================== TELEGRAM COMMANDS ===================================
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Skiddle-ID Full Blocklist Monitor\n\n"
        "Commands:\n"
        "/add example.com\n/remove example.com\n/list\n/status (check now)\n"
        "/pause  → stop hourly checks\n/resume → start hourly checks again\n\n"
        "Only alerts you when status actually changes"
    )

async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /add example.com")
        return
    domain = context.args[0].lower().replace("https://","").replace("http://","").split("/")[0].lstrip("www.")
    chat_id = update.effective_chat.id
    c.execute("INSERT OR IGNORE INTO domains (chat_id, domain) VALUES (?, ?)", (chat_id, domain))
    conn.commit()
    await update.message.reply_text(f"Added {domain}")

async def remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /remove example.com")
        return
    domain = context.args[0].lower().replace("https://","").split("/")[0].lstrip("www.")
    chat_id = update.effective_chat.id
    c.execute("DELETE FROM domains WHERE chat_id=? AND domain=?", (chat_id, domain))
    conn.commit()
    await update.message.reply_text(f"Removed {domain}")

async def list_domains(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    c.execute("SELECT domain, last_status FROM domains WHERE chat_id=?", (chat_id,))
    rows = c.fetchall()
    if not rows:
        await update.message.reply_text("Your list is empty")
        return
    msg = "*Your domains:*\n\n"
    for d, s in rows:
        emoji = "BLOCKED" if s == "BLOCKED" else "CLEAN" if s == "CLEAN" else "?"
        msg += f"{emoji} {d} → {s}\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Checking all your domains now…")
    await hourly_check(context)

async def pause(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    c.execute("INSERT OR REPLACE INTO settings (chat_id, paused) VALUES (?, 1)", (chat_id,))
    conn.commit()
    await update.message.reply_text("Hourly checks PAUSED")

async def resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    c.execute("INSERT OR REPLACE INTO settings (chat_id, paused) VALUES (?, 0)", (chat_id,))
    conn.commit()
    await update.message.reply_text("Hourly checks RESUMED")

# =================================== HOURLY TASK ===================================
async def hourly_check(context: ContextTypes.DEFAULT_TYPE = None):
    refresh_full_blocklist()        # ← always uses ALL txt files

    c.execute("SELECT chat_id, domain, last_status FROM domains")
    for chat_id, domain, last in c.fetchall():
        current = "BLOCKED" if domain in blocked_set or f"www.{domain}" in blocked_set else "CLEAN"

        if current != last:
            emoji = "BLOCKED" if current == "BLOCKED" else "CLEAN"
            text = f"{emoji} *{domain}* is now *{current}* in Kominfo blocklist\nhttps://github.com/Skiddle-ID/blocklist"
            await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")

            c.execute("UPDATE domains SET last_status=? WHERE chat_id=? AND domain=?", (current, chat_id, domain))
            conn.commit()

async def scheduled_task(app):
    # Skip paused users
    c.execute("SELECT chat_id FROM settings WHERE paused = 1")
    paused = {row[0] for row in c.fetchall()}

    c.execute("SELECT DISTINCT chat_id FROM domains")
    users = {row[0] for row in c.fetchall()}

    for chat_id in users - paused:
        class Dummy: bot = app.bot
        await hourly_check(Dummy())

# =================================== MAIN ===================================
if __name__ == "__main__":
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("add", add))
    app.add_handler(CommandHandler("remove", remove))
    app.add_handler(CommandHandler("list", list_domains))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("pause", pause))
    app.add_handler(CommandHandler("resume", resume))

    # Check every hour (first run after 60 seconds)
    app.job_queue.run_repeating(scheduled_task, interval=3600, first=60)

    print("Bot started — monitoring ALL txt files from Skiddle-ID/blocklist")
    app.run_polling(drop_pending_updates=True)
