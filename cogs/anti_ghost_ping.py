import discord
from discord.ext import commands

class AntiGhostPing(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _handle_ghost_ping(self, message: discord.Message, mentions, action_type="刪除", lost_roles=None, lost_everyone=False, after: discord.Message = None):
        """處理幽靈提及的核心邏輯"""
        # 排除機器人自己與作者本人的提及
        filtered_mentions = [m for m in mentions if not m.bot and m.id != message.author.id]
        
        # 如果沒有遺失任何提及（成員、身分組、或 Everyone），就跳過
        if not filtered_mentions and not lost_roles and not lost_everyone:
            return

        # 1. 在原頻道發送簡短幽靈提及提醒（不顯示原始內容、已刪除內容等）
        channel_embed = discord.Embed(
            title="👻 偵測到幽靈提及 (Ghost Ping)！",
            description=f"有一個由 {message.author.mention} 發送的提及被刪除了。",
            color=discord.Color.from_rgb(255, 87, 87), # 鮮紅色
            timestamp=discord.utils.utcnow()
        )
        channel_embed.set_footer(text=f"訊息 ID: {message.id}")

        try:
            await message.channel.send(embed=channel_embed, allowed_mentions=discord.AllowedMentions.none())
        except discord.Forbidden:
            pass # 忽略權限不足的情況

        # 2. 將幽靈提及的詳細內容（編輯前後內容、刪除的內容、消失的提及）發送到訊息編輯與刪除紀錄頻道
        log_channel_id = self.bot.config.get("message_logger_channel_id", 0)
        log_channel = message.guild.get_channel(log_channel_id)
        
        if log_channel:
            log_embed = discord.Embed(
                title=f"👻 偵測到幽靈提及 (Ghost Ping) - 訊息已{action_type}",
                color=discord.Color.from_rgb(255, 87, 87),
                timestamp=discord.utils.utcnow()
            )
            log_embed.set_author(name=f"{message.author} ({message.author.id})", icon_url=message.author.display_avatar.url)
            log_embed.add_field(name="作者", value=message.author.mention, inline=True)
            log_embed.add_field(name="頻道", value=message.channel.mention, inline=True)
            
            mention_list = []
            if lost_everyone:
                mention_list.append("@everyone / @here")
            if filtered_mentions:
                mention_list.append(" ".join(m.mention for m in filtered_mentions))
            if lost_roles:
                mention_list.append(" ".join(r.mention for r in lost_roles))

            if mention_list:
                log_embed.add_field(name="消失的提及", value="\n".join(mention_list), inline=False)

            if action_type == "刪除":
                content = message.content if message.content else "*無文字內容*"
                if len(content) > 1024:
                    content = content[:1021] + "..."
                log_embed.add_field(name="刪除的內容", value=content, inline=False)
            elif action_type == "編輯":
                if after:
                    log_embed.add_field(name="跳轉連結", value=f"[點我跳轉]({after.jump_url})", inline=False)
                before_content = message.content if message.content else "*無文字內容*"
                after_content = after.content if (after and after.content) else "*無文字內容*"
                
                if len(before_content) > 1024:
                    before_content = before_content[:1021] + "..."
                if len(after_content) > 1024:
                    after_content = after_content[:1021] + "..."
                
                log_embed.add_field(name="編輯前內容", value=before_content, inline=False)
                log_embed.add_field(name="編輯後內容", value=after_content, inline=False)

            log_embed.set_footer(text=f"訊息 ID: {message.id}")

            try:
                await log_channel.send(embed=log_embed)
            except discord.Forbidden:
                pass
            except Exception as e:
                print(f"Failed to send ghost ping log: {e}")

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
            await self._handle_ghost_ping(before, lost_mentions, "編輯", lost_roles=lost_roles, lost_everyone=lost_everyone, after=after)

def setup(bot):
    bot.add_cog(AntiGhostPing(bot))
