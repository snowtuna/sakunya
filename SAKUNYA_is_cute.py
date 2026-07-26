#sakunya is at your service

import discord
from discord.ext import commands
from collections import defaultdict, deque
import time
import re
import os
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="^w^ ", intents=intents)

TIME_WINDOW = 2
MAX_MESSAGES = 4      

INVITE_REGEX = re.compile(
    r"(?:https?://)?(?:www\.)?(?:discord\.(?:gg|io|me|li)|discord(?:app)?\.com/invite)/\w+",
    re.IGNORECASE
)

user_message_times = defaultdict(lambda: deque(maxlen=MAX_MESSAGES))

@bot.event
async def on_ready():
    print("Sakunya is at your service.")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.author.guild_permissions.administrator:
        await bot.process_commands(message)
        return

    current_time = time.time()
    user_id = message.author.id
    channel = message.channel


    if INVITE_REGEX.search(message.content):
        try:
            await message.delete()
            await message.author.ban(reason="Unauthorized Discord invite link sent")
            
            embed = discord.Embed(
                title="🛡️ Sakunya - Raid/Ban Notice",
                description=f"User: {message.author.mention} (`{message.author.id}`)\nReason: Unauthorized Discord invite link.",
                color=discord.Color.red()
            )
            embed.set_footer(text="Unauthorized links are not permitted.")
            
            await channel.send(embed=embed)
            return
        except discord.Forbidden:
            print("uwa! Please check my permissions. I can't delete messages or ban users.")
            return

    timestamps = user_message_times[user_id]
    

    while timestamps and current_time - timestamps[0][0] > TIME_WINDOW:
        timestamps.popleft()

    timestamps.append((current_time, message))


    if len(timestamps) >= MAX_MESSAGES:
        try:

            await message.author.ban(reason="Spamming is not allowed!")
            for _, msg in list(timestamps):
                try:
                    await msg.delete()
                except (discord.NotFound, discord.Forbidden):
                    pass

            embed = discord.Embed(
                title="🛡️ Sakunya  - Raid/Spam Notice",
                description=f"User: {message.author.mention} (`{message.author.id}`)\nReason: Message spam frequency exceeded the limit.",
                color=discord.Color.orange()
            )
            embed.set_footer(text="Raiding or spamming are not welcomed.")
            await channel.send(embed=embed)
            
            timestamps.clear()
            return
        except discord.Forbidden:
            print("uwa! Please check my permissions. I can't delete messages or ban users.")

    await bot.process_commands(message)

@bot.command(name="info")
async def info(ctx):
    embed = discord.Embed(
        title="✨ Sakunya Bot Info",
        description="Sakunya is actively protecting this server from spam and unauthorized invite links!\n\n"
        "*More features will be added in the future!*",
        color=discord.Color.blurple()
    )
    embed.set_footer(text="Sakunya is always at your service - 26 Jul 2026")
    
    await ctx.send(embed=embed)

bot.run(os.getenv("TOKEN"))
