import time, datetime
from collections import defaultdict, deque
import discord
from discord.ext import commands
import config

server_penalties = {}

async def get_penalty_mem(guild_id: int, violation_type: str) -> dict:
    if guild_id not in server_penalties:
        server_penalties[guild_id] = {
            "spam": {"action": "ban", "duration": 0},
            "invite": {"action": "ban", "duration": 0}
        }
    return server_penalties[guild_id].get(violation_type, {"action": "ban", "duration": 0})

async def set_penalty_mem(guild_id: int, violation_type: str, action: str, duration: int):
    if guild_id not in server_penalties:
        server_penalties[guild_id] = {
            "spam": {"action": "ban", "duration": 0},
            "invite": {"action": "ban", "duration": 0}
        }
    server_penalties[guild_id][violation_type] = {"action": action, "duration": duration}


class DurationModal(discord.ui.Modal):
    def __init__(self, action_name: str, parent_view):
        super().__init__(title=f"Set Duration for {action_name.capitalize()}")
        self.parent_view = parent_view
        self.action_name = action_name
        self.duration_input = discord.ui.TextInput(
            label="Duration in seconds (0 = Permanent/Default)",
            placeholder="e.g. 60, 3600, 86400",
            default="0",
            required=True
        )
        self.add_item(self.duration_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            val = int(self.duration_input.value)
            if val < 0:
                raise ValueError
        except ValueError:
            await interaction.response.send_message("Invalid input! Please enter a non-negative integer.", ephemeral=True)
            return
        
        await set_penalty_mem(
            self.parent_view.guild.id,
            self.parent_view.current_target,
            self.action_name,
            val
        )
        embed = await self.parent_view.build_embed()
        await interaction.response.edit_message(embed=embed, view=self.parent_view)

class PenaltySelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Spam / Raid", value="spam", emoji="🛡️"),
            discord.SelectOption(label="Invite Link", value="invite", emoji="🔗")
        ]
        super().__init__(placeholder="Select Violation Type to Configure...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        self.view.current_target = self.values[0]
        embed = await self.view.build_embed()
        await interaction.response.edit_message(embed=embed, view=self.view)

class SettingsView(discord.ui.View):
    def __init__(self, guild: discord.Guild, author_id: int):
        super().__init__(timeout=60)
        self.guild = guild
        self.author_id = author_id
        self.current_target = "spam"
        self.add_item(PenaltySelect())

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Unable to access.", ephemeral=True)
            return False
        return True

    async def _format_penalty(self, target: str) -> str:
        data = await get_penalty_mem(self.guild.id, target)
        act = data["action"].capitalize()
        dur = data["duration"]
        if act == "Kick":
            return "Kick (N/A)"
        if dur == 0:
            return f"{act} (Permanent)"
        return f"{act} ({dur} secs)"

    async def build_embed(self) -> discord.Embed:
        target_display = "🛡️ Spam / Raid" if self.current_target == "spam" else "🔗 Invite Link"
        spam_str = await self._format_penalty("spam")
        invite_str = await self._format_penalty("invite")

        embed = discord.Embed(
            title=f"⚙️ Sakunya Security Settings - {self.guild.name}",
            description=(
                f"Server: **{self.guild.name}** (`{self.guild.id}`)\n"
                f"Currently Editing: **{target_display}**\n\n"
                f"🛡️ **Spam Penalty:** {spam_str}\n"
                f"🔗 **Invite Link Penalty:** {invite_str}\n\n"
                f"Use the dropdown to select which setting to modify, then click buttons below."
            ),
            color=discord.Color.blurple()
        )
        embed.set_footer(text="sakunya")
        return embed

    @discord.ui.button(label="Ban", style=discord.ButtonStyle.danger, emoji="🔨")
    async def ban_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = DurationModal("ban", self)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Kick", style=discord.ButtonStyle.secondary, emoji="👢")
    async def kick_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await set_penalty_mem(self.guild.id, self.current_target, "kick", 0)
        embed = await self.build_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Timeout", style=discord.ButtonStyle.secondary, emoji="⏱️")
    async def timeout_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = DurationModal("timeout", self)
        await interaction.response.send_modal(modal)

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True

class Security(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.user_message_times = defaultdict(lambda: deque(maxlen=config.MAXMSG))

    async def _punish_user(self, member, channel, title, reason, footer, penalty_key="spam"):
        cfg = await get_penalty_mem(member.guild.id, penalty_key)
        action = cfg["action"]
        duration = cfg["duration"]
        
        try:
            if action == "ban":
                await member.ban(reason=reason, delete_message_seconds=3600)
            elif action == "kick":
                await member.kick(reason=reason)
            elif action == "timeout":
                secs = duration if duration > 0 else 3600
                await member.timeout(datetime.timedelta(seconds=secs), reason=reason)

            embed = discord.Embed(
                title=title, 
                description=f"User: {member.mention} (`{member.id}`)\nReason: {reason}", 
                color=discord.Color.red()
            )
            embed.set_footer(text=footer)
            await channel.send(embed=embed)
        except discord.Forbidden:
            print("uwah! Please check my permissions. I can't delete messages or ban users.")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        if not message.author.guild_permissions.administrator:
            content_lower = message.content.lower()
            
            if any(k in content_lower for k in ["discord.gg/", "discord.com/invite/", "discordapp.com/invite/"]):
                await self._punish_user(
                    message.author, 
                    message.channel, 
                    "🛡️ Sakunya - Raid/Ban Notice", 
                    "Unauthorized Discord invite link.", 
                    "Unauthorized links are not permitted.",
                    penalty_key="invite"
                )
                return

            now = time.time()
            times = self.user_message_times[message.author.id]
            while times and now - times[0] > config.TIMEWINDOW:
                times.popleft()
            times.append(now)

            if len(times) >= config.MAXMSG:
                times.clear()
                await self._punish_user(
                    message.author, 
                    message.channel, 
                    "🛡️ Sakunya - Raid/Spam Notice", 
                    "Message spam frequency exceeded the limit.", 
                    "Raiding or spamming are not welcomed.",
                    penalty_key="spam"
                )
                return

    @commands.command(name="setpenalty")
    async def setpenalty(self, ctx):
        if not ctx.guild or ctx.author.id != ctx.guild.owner_id:
            return

        try:
            await ctx.message.delete()
        except Exception:
            pass

        view = SettingsView(ctx.guild, ctx.author.id)
        embed = await view.build_embed()
        try:
            await ctx.author.send(embed=embed, view=view)
        except discord.Forbidden:
            pass

async def setup(bot):
    await bot.add_cog(Security(bot))