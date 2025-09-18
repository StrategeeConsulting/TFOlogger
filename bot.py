import discord
from discord.ext import commands
import os
from flask import Flask
import threading
import re
import json

# 🔧 Intents setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# 🤖 Bot setup
bot = commands.Bot(command_prefix="!", intents=intents)

# 🗑 Deleted messages log
deleted_messages = []

# 💾 JSON storage
DATA_FILE = "deleted_messages.json"
EVENT_LOG_FILE = "user_events.json"
WATCHLIST_FILE = "watchlist.json"

user_events = []
watchlist = []

def save_deleted_messages():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(deleted_messages, f, default=str, indent=2)

def load_deleted_messages():
    global deleted_messages
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            deleted_messages = json.load(f)
    except FileNotFoundError:
        deleted_messages = []

def save_user_events():
    with open(EVENT_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(user_events, f, indent=2)

def load_user_events():
    global user_events
    try:
        with open(EVENT_LOG_FILE, "r", encoding="utf-8") as f:
            user_events = json.load(f)
    except FileNotFoundError:
        user_events = []

def save_watchlist():
    with open(WATCHLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(watchlist, f, indent=2)

def load_watchlist():
    global watchlist
    try:
        with open(WATCHLIST_FILE, "r", encoding="utf-8") as f:
            watchlist = json.load(f)
    except FileNotFoundError:
        watchlist = []

# 🚨 Suspicious keywords and domains
SUSPICIOUS_KEYWORDS = ["password", "token", "leak", "ban", "cheat", "dm me"]
SUSPICIOUS_DOMAINS = ["bit.ly", "tinyurl.com", "discord.gg", "grabify.link"]

# 🔍 Link extractor
def extract_links(text):
    return re.findall(r'https?://\S+', text)

# 📄 Pagination helper
def paginate(text, limit=1900):
    lines = text.split('\n')
    pages, current = [], ""
    for line in lines:
        if len(current) + len(line) + 1 > limit:
            pages.append(current)
            current = ""
        current += line + "\n"
    pages.append(current)
    return pages

# ✅ Bot ready event
@bot.event
async def on_ready():
    load_deleted_messages()
    load_user_events()
    load_watchlist()
    activity = discord.Game(name="YOU'RE BEING MONITORED")
    await bot.change_presence(status=discord.Status.online, activity=activity)
    print(f"✅ Logged in as {bot.user}")

# 🗑 Message deleted event
@bot.event
async def on_message_delete(message: discord.Message):
    if message.guild is None:
        return

    content_lower = message.content.lower()
    links = extract_links(message.content)
    flagged = any(word in content_lower for word in SUSPICIOUS_KEYWORDS) or any(domain in link for link in links for domain in SUSPICIOUS_DOMAINS)

    deleted_messages.append({
        "author_id": message.author.id,
        "author_name": message.author.display_name,
        "content": message.content,
        "timestamp": str(message.created_at),
        "flagged": flagged
    })
    save_deleted_messages()

    user_events.append({
        "user_id": message.author.id,
        "user_name": message.author.display_name,
        "event": "Deleted message",
        "content": message.content,
        "timestamp": str(message.created_at)
    })
    save_user_events()

    recent_deletions = [e for e in user_events if e["user_id"] == message.author.id and e["event"] == "Deleted message"]
    if len(recent_deletions) >= 5:
        if not any(w["user_id"] == message.author.id for w in watchlist):
            watchlist.append({
                "user_id": message.author.id,
                "user_name": message.author.display_name,
                "reason": "Deleted 5+ messages recently",
                "timestamp": str(message.created_at)
            })
            save_watchlist()

    await log_message("🗑 Message Deleted", message)

    if flagged:
        alert_channel = bot.get_channel(LOG_CHANNEL_ID)
        if alert_channel:
            await alert_channel.send(f"⚠️ Suspicious deleted message by {message.author.mention}:\n`{message.content}`")

# ✏️ Message edited event
@bot.event
async def on_message_edit(before: discord.Message, after: discord.Message):
    if before.guild is None or before.content == after.content:
        return

    user_events.append({
        "user_id": before.author.id,
        "user_name": before.author.display_name,
        "event": "Edited message",
        "content": f"{before.content} → {after.content}",
        "timestamp": str(before.created_at)
    })
    save_user_events()

    await log_message("✏️ Message Edited", before, before=before.content, after=after.content)

@bot.event
async def on_member_join(member):
    user_events.append({
        "user_id": member.id,
        "user_name": member.display_name,
        "event": "Joined server",
        "content": "",
        "timestamp": str(member.joined_at)
    })
    save_user_events()

@bot.event
async def on_member_remove(member):
    user_events.append({
        "user_id": member.id,
        "user_name": member.display_name,
        "event": "Left server",
        "content": "",
        "timestamp": str(discord.utils.utcnow())
    })
    save_user_events()

@bot.event
async def on_member_update(before, after):
    if before.roles != after.roles:
        added = [r.name for r in after.roles if r not in before.roles]
        removed = [r.name for r in before.roles if r not in after.roles]
        changes = []
        if added:
            changes.append(f"Added: {', '.join(added)}")
        if removed:
            changes.append(f"Removed: {', '.join(removed)}")
        user_events.append({
            "user_id": after.id,
            "user_name": after.display_name,
            "event": "Role update",
            "content": "; ".join(changes),
            "timestamp": str(discord.utils.utcnow())
        })
        save_user_events()

# 🔍 Command: !deletedby
@bot.command()
async def deletedby(ctx, member: discord.Member):
    results = [msg for msg in deleted_messages if msg["author_id"] == member.id]
    if not results:
        await ctx.send(f"No deleted messages found for {member.display_name}.")
        return

    response = f"Deleted messages by {member.display_name}:\n"
    for msg in results[-5:]:
        timestamp = msg["timestamp"]
        response += f"[{timestamp}] {msg['content']}\n"

    for page in paginate(response):
        await ctx.send(page)

# 🔍 Command: !searchdeleted
@bot.command()
async def searchdeleted(ctx, *, keyword: str):
    results = [msg for msg in deleted_messages if keyword.lower() in msg["content"].lower()]
    if not results:
        await ctx.send(f"No deleted messages found containing '{keyword}'.")
        return

    response = f"Deleted messages containing '{keyword}':\n"
    for msg in results:
        timestamp = msg["timestamp"]
        response += f"[{timestamp}] {msg['author_name']}: {msg['content']}\n"

    for page in paginate(response):
        await ctx.send(page)

# 🔍 Command: !replay
@bot.command()
async def replay(ctx, member: discord.Member):
    events = [e for e in user_events if e["user_id"] == member.id]
    if not events:
        await ctx.send(f"No recent activity found for {member.display_name}.")
        return

    response = f"Incident Replay for {member.display_name}:\n"
    for e in events[-10:]:
        response += f"[{e['timestamp']}] {e['event']}: {e['content']}\n"

    for page in paginate(response):
        await ctx.send(page)

# 🔍 Command: !watchlist
@bot.command()
async def watchlist(ctx):
    if not watchlist:
        await ctx.send("No users currently flagged.")
        return

    response = "⚠️ Behavioral Watchlist:\n"
    for w in watchlist:
        response += f"[{w['timestamp']}] {w['user_name']}: {w['reason']}\n"

    for page in paginate(response):
        await ctx.send(page)

# 📋 Logging function
LOG_SERVER_ID = 1365466210266779709
LOG_CHANNEL_ID = 1417980114557210624

async def log_message(event_title: str, message: discord.Message, before: str = None, after: str = None):
    log_server = bot.get_guild(LOG_SERVER_ID)
    log_channel = log_server.get_channel(LOG_CHANNEL_ID)
    if log_channel is None:
        print("⚠️ Log channel not found.")
        return

    embed = discord.Embed(
        title=event_title,
        description=f"**Author:** {message.author.mention}\n**Channel:** {message.channel.mention} (Server: {message.guild.name})",
        color=discord.Color.orange() if "Edited" in event_title else discord.Color.red()
    )

    if before is not None:
        embed.add_field(name="Before", value=before or "*(no content)*", inline=False)
    if after is not None:
        embed.add_field(name="After", value=after or "*(no content)*", inline=False)
    if before is None and after is None and message.content:
        embed.add_field(name="Content", value=message.content, inline=False)

    files_to_send = []
    for attachment in message.attachments:
        try:
            fp = await attachment.to_file()
            files_to_send.append(fp)
        except Exception as e:
            embed.add_field(name="Attachment Error", value=str(e), inline=False)

    if message.embeds:
        for i, e in enumerate(message.embeds, start=1):
            details = []
            if e.title:
                details.append(f"**Title:** {e.title}")
            if e.description:
                details.append(f"**Description:** {e.description[:200]}{'...' if len(e.description) > 200 else ''}")
            if e.url:
                details.append(f"**URL:** {e.url}")
            if details:
                embed.add_field(name=f"Embed {i}", value="\n".join(details), inline=False)

    await log_channel.send(embed=embed, files=files_to_send)

    # 🌐 Flask web server for Render
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_web():
    app.run(host='0.0.0.0', port=10000, use_reloader=False)


# 🚀 Keep Flask and bot alive
if __name__ == "__main__":
    run_web()
    bot.run(os.getenv("DISCORD_TOKEN"))

