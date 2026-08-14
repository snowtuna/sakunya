import asyncio
import discord
from discord.ext import commands
import config

intents = discord.Intents.default()
intents.message_content = intents.guilds = intents.members = True

bot = commands.Bot(command_prefix=config.PREFIX, intents=intents)

@bot.event
async def on_ready():
    print("sakunya is at your service.")
    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.CustomActivity(name="^w^ info // sakunya is now protecting your server🗡️", emoji="🗡️")
    )

async def main():
    async with bot:
        await bot.load_extension("cogs.utility")
        await bot.load_extension("cogs.security")
        await bot.start(config.TOKEN)

if __name__ == "__main__":
    asyncio.run(main())