import os, time
from collections import defaultdict, deque
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.message_content = intents.guilds = intents.members = True

bot = commands.Bot(command_prefix="^w^ ", intents=intents)

timewindow = int(os.getenv("timewindow", 2))
maxmsg = int(os.getenv("maxmsg", 4))
user_message_times = defaultdict(lambda: deque(maxlen=maxmsg))

class CommandPaginator(discord.ui.View):
    def __init__(self, pages, author_id):
        super().__init__(timeout=60)
        self.pages, self.author_id, self.current_page = pages, author_id, 0
        self.next_button.disabled = (len(pages) <= 1)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Unable to access.", ephemeral=True)
            return False
        return True

    async def _change_page(self, interaction: discord.Interaction, diff: int):
        self.current_page += diff
        self.prev_button.disabled = (self.current_page == 0)
        self.next_button.disabled = (self.current_page == len(self.pages) - 1)
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)

    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary, disabled=True)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._change_page(interaction, -1)

    @discord.ui.button(label="▶", style=discord.ButtonStyle.primary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._change_page(interaction, 1)

@bot.event
async def on_ready():
    print("sakunya is at your service.")
    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.CustomActivity(name="^w^ info // sakunya is now protecting your server🗡️", emoji="🗡️")
    )

async def _punish_user(member, channel, title, reason, footer):
    try:
        await member.ban(reason=reason, delete_message_seconds=3600)
        embed = discord.Embed(
            title=title, 
            description=f"User: {member.mention} (`{member.id}`)\nReason: {reason}", 
            color=discord.Color.red()
        )
        embed.set_footer(text=footer)
        await channel.send(embed=embed)
    except discord.Forbidden:
        print("uwah! Please check my permissions. I can't delete messages or ban users.")

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    if not message.author.guild_permissions.administrator:
        content_lower = message.content.lower()
        
        if any(k in content_lower for k in ["discord.gg/", "discord.com/invite/", "discordapp.com/invite/"]):
            await _punish_user(
                message.author, 
                message.channel, 
                "🛡️ Sakunya - Raid/Ban Notice", 
                "Unauthorized Discord invite link.", 
                "Unauthorized links are not permitted."
            )
            return

        now = time.time()
        times = user_message_times[message.author.id]
        while times and now - times[0] > timewindow:
            times.popleft()
        times.append(now)

        if len(times) >= maxmsg:
            times.clear()
            await _punish_user(
                message.author, 
                message.channel, 
                "🛡️ Sakunya - Raid/Spam Notice", 
                "Message spam frequency exceeded the limit.", 
                "Raiding or spamming are not welcomed."
            )
            return

    await bot.process_commands(message)

@bot.command(name="info")
async def info(ctx):
    embed = discord.Embed(
        title="✨ Sakunya Bot Info",
        description="Sakunya is actively protecting this server from spam and unauthorized invite links!\n"
                    "Check out the commands by using `^w^ cmd` \n\n"
                    "*More features will be added in the future!*",
        color=discord.Color.blurple(),
        timestamp=discord.utils.utcnow()
    )
    embed.set_footer(text="sakunya")
    await ctx.send(embed=embed)

@bot.command(name="clear")
@commands.has_permissions(administrator=True)
async def clear(ctx):
    deleted = await ctx.channel.purge(
        limit=100, 
        check=lambda m: m.author == bot.user in (m.embeds[0].title or "")
    )
    embed = discord.Embed(
        title="🧹 Sakunya is cleaning...",
        description=f"Sakunya has cleared {len(deleted)} messages.\n\n*This message will be deleted in 5 seconds.*",
        color=discord.Color.light_grey()
    )
    msg = await ctx.send(embed=embed)
    await msg.delete(delay=5)

@bot.command(name="cmd")
async def cmd(ctx):
    try:
        with open("commands.txt", "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return

    if not lines:
        return

    ipp = 10
    total_pages = (len(lines) - 1) // ipp + 1
    pages = []

    for i in range(0, len(lines), ipp):
        chunk = lines[i:i + ipp]
        embed = discord.Embed(
            description="\n".join(f"{cmd_name}" for cmd_name in chunk),
            title="📖 Sakunya's Command List", 
            color=discord.Color.blurple(), 
            timestamp=discord.utils.utcnow()
        )
        embed.set_footer(text=f"{(i // ipp) + 1} / {total_pages} - sakunya")
        pages.append(embed)

    view = CommandPaginator(pages, ctx.author.id) if len(pages) > 1 else None
    await ctx.send(embed=pages[0], view=view)

bot.run(os.getenv("TOKEN"))