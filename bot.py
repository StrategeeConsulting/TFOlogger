import discord
from discord.ext import commands
import os
from flask import Flask
import threading
import re

# 🔧 Intents setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# 🤖 Bot setup
bot = commands.Bot(command_prefix="!", intents=intents)

# 🗑 Deleted messages log
deleted_messages = []

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
        "timestamp": message.created_at,
        "flagged": flagged
    })

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
    await log_message("✏️ Message Edited", before, before=before.content, after=after.content)

# 🔍 Command: !deletedby
@bot.command()
async def deletedby(ctx, member: discord.Member):
    results = [msg for msg in deleted_messages if msg["author_id"] == member.id]
    if not results:
        await ctx.send(f"No deleted messages found for {member.display_name}.")
        return

    response = f"Deleted messages by {member.display_name}:\n"
    for msg in results[-5:]:
        timestamp = msg["timestamp"].strftime("%Y-%m-%d %H:%M")
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
        timestamp = msg["timestamp"].strftime("%Y-%m-%d %H:%M")
        response += f"[{timestamp}] {msg['author_name']}: {msg['content']}\n"

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
    app.run(host='0.0.0.0', port=10000)
threading.Thread(target=run_web).start()

# 🚀 Run the bot
bot.run(os.getenv("DISCORD_TOKEN"))