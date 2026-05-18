import discord
from discord.ext import commands

class AntiGhostPing(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _handle_ghost_ping(self, message: discord.Message, mentions, action_type="刪除", lost_roles=None, lost_everyone=False):
        """處理幽靈提及的核心邏輯"""
        # 排除機器人自己與作者本人的提及
        filtered_mentions = [m for m in mentions if not m.bot and m.id != message.author.id]
        
        # 如果沒有遺失任何提及（成員、身分組、或 Everyone），就跳過
        if not filtered_mentions and not lost_roles and not lost_everyone:
            return

        embed = discord.Embed(
            title="👻 偵測到幽靈提及 (Ghost Ping)！",
            description=f"發現一則訊息被 **{action_type}**，但其中包含的提及已消失。",
            color=discord.Color.from_rgb(255, 87, 87), # 鮮紅色
            timestamp=discord.utils.utcnow()
        )

        embed.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
        embed.add_field(name="作者", value=message.author.mention, inline=True)
        embed.add_field(name="頻道", value=message.channel.mention, inline=True)
        
        mention_list = []
        if lost_everyone:
            mention_list.append("@everyone / @here")
        if filtered_mentions:
            mention_list.append(" ".join(m.mention for m in filtered_mentions))
        if lost_roles:
            mention_list.append(" ".join(r.mention for r in lost_roles))

        if mention_list:
            embed.add_field(name="消失的提及", value="\n".join(mention_list), inline=False)

        if message.content:
            # 限制顯示字數，避免 Embed 過長
            clean_content = message.content[:1000] + ("..." if len(message.content) > 1000 else "")
            embed.add_field(name="訊息內容", value=clean_content, inline=False)

        embed.set_footer(text=f"訊息 ID: {message.id}")

        # 使用 allowed_mentions=discord.AllowedMentions.none() 確保機器人發出的 Embed 不會再次觸發 Ping
        try:
            await message.channel.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())
        except discord.Forbidden:
            pass # 忽略權限不足的情況

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        
        await self._handle_ghost_ping(
            message, 
            message.mentions, 
            "刪除", 
            lost_roles=message.role_mentions, 
            lost_everyone=message.mention_everyone
        )

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot or not before.guild:
            return
        
        # 找出在編輯後消失的提及
        lost_mentions = [m for m in before.mentions if m not in after.mentions]
        lost_roles = [r for r in before.role_mentions if r not in after.role_mentions]
        lost_everyone = before.mention_everyone and not after.mention_everyone
        
        if lost_mentions or lost_roles or lost_everyone:
            await self._handle_ghost_ping(before, lost_mentions, "編輯", lost_roles=lost_roles, lost_everyone=lost_everyone)

def setup_anti_ghost_ping(bot):
    bot.add_cog(AntiGhostPing(bot))
