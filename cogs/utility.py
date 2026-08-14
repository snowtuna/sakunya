import discord
from discord.ext import commands
import os

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

class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="info")
    async def info(self, ctx):
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

    @commands.command(name="clear")
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx, search_limit: int = 70):
        def bot_or_cmd(m):
            return m.author == self.bot.user or m.content.startswith(self.bot.command_prefix)
        deleted = await ctx.channel.purge(
            limit=search_limit,
            check=bot_or_cmd)

        embed = discord.Embed(
            title="🧹 Sakunya is cleaning...",
            description=f"Sakunya has cleared {len(deleted)} messages.\n\n*This message will be deleted in 5 seconds.*",
            color=discord.Color.light_grey()
        )
        msg = await ctx.send(embed=embed)
        await msg.delete(delay=5)

    @commands.command(name="cmd")
    async def cmd(self, ctx):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        file_path = os.path.join(base_dir, "commands.txt")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
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

async def setup(bot):
    await bot.add_cog(Utility(bot))