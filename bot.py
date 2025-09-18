import discord
from discord.ext import commands

deleted_messages = []
@bot.event
async def on_message_delete(message: discord.Message):
    deleted_messages.append({
        "author": message.author,
        "content": message.content,
        "timestamp": message.created_at
    })
    await log_message("Message Deleted", message)

deleted_messages = []

@bot.event
async def on_message_delete(message: discord.Message):
    deleted_messages.append({
        "author": message.author,
        "content": message.content,
        "timestamp": message.created_at
    })
    await log_message("Message deleted", message)

@bot.command()
async def deletedby(ctx, member: discord.Member):
    results = [msg for msg in deleted_messages if msg["author"].id == member.id]

    if not results:
        await ctx.send(f"No deleted messages found for {member.display_name}.")
        return

    response = f"Deleted messages by {member.display_name}:\n"
    for msg in results[-5:]:  # Show last 5
        timestamp = msg["timestamp"].strftime("%Y-%m-%d %H:%M")
        response += f"[{timestamp}] {msg['content']}\n"

    await ctx.send(response)
    
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

bot = commands.Bot(command_prefix="!", intents=intents)

# Server & Channel ID
LOG_SERVER_ID = 1365466210266779709
LOG_CHANNEL_ID = 1417980114557210624

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

async def log_message(event_title: str, message: discord.Message, before: str = None, after: str = None):
    log_server = bot.get_guild(LOG_SERVER_ID)
    log_channel = log_server.get_channel(LOG_CHANNEL_ID)

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
    # Bot Re-upload attachments 
    for attachment in message.attachments:
        try:
            fp = await attachment.to_file()
            files_to_send.append(fp)
        except Exception as e:
            embed.add_field(name="Attachment Error", value=str(e), inline=False)

    # Summarize embeds
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

@bot.event
async def on_message_delete(message: discord.Message):
    if message.guild is None:
        return
    await log_message("🗑 Message Deleted", message)

@bot.event
async def on_message_edit(before: discord.Message, after: discord.Message):
    if before.guild is None or before.content == after.content:
        return
    await log_message("✏️ Message Edited", before, before=before.content, after=after.content)

import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    activity = discord.Game(name="YOU'RE BEING MONITORED")
    await bot.change_presence(status=discord.Status.online, activity=activity)
    print(f"Logged in as {bot.user}")


import os
bot.run(os.getenv("DISCORD_TOKEN"))

from flask import Flask
import threading

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_web():
    app.run(host='0.0.0.0', port=10000)

threading.Thread(target=run_web).start()

