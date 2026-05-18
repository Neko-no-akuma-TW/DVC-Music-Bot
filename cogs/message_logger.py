import discord
from discord.ext import commands
import datetime

class MessageLogger(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _get_log_channel(self, guild):
        """從全域設定獲取記錄頻道"""
        channel_id = self.bot.config.get("message_logger_channel_id", 0)
        return guild.get_channel(channel_id)

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        log_channel = self._get_log_channel(message.guild)
        if not log_channel:
            return

        embed = discord.Embed(
            title="🗑️ 訊息已刪除",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now()
        )
        embed.set_author(name=f"{message.author} ({message.author.id})", icon_url=message.author.display_avatar.url)
        embed.add_field(name="頻道", value=message.channel.mention, inline=True)
        embed.add_field(name="作者", value=message.author.mention, inline=True)
        
        content = message.content if message.content else "*無文字內容*"
        if len(content) > 1024:
            content = content[:1021] + "..."
        embed.add_field(name="內容", value=content, inline=False)

        if message.attachments:
            attachment_names = ", ".join([a.filename for a in message.attachments])
            embed.add_field(name="附件", value=attachment_names, inline=False)

        embed.set_footer(text=f"訊息 ID: {message.id}")
        
        try:
            await log_channel.send(embed=embed)
        except discord.Forbidden:
            pass

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot or not before.guild or before.content == after.content:
            return

        log_channel = self._get_log_channel(before.guild)
        if not log_channel:
            return

        embed = discord.Embed(
            title="📝 訊息已編輯",
            color=discord.Color.orange(),
            timestamp=datetime.datetime.now()
        )
        embed.set_author(name=f"{before.author} ({before.author.id})", icon_url=before.author.display_avatar.url)
        embed.add_field(name="頻道", value=before.channel.mention, inline=True)
        embed.add_field(name="作者", value=before.author.mention, inline=True)
        embed.add_field(name="[跳轉至訊息]", value=after.jump_url, inline=False)

        before_content = before.content if before.content else "*無文字內容*"
        after_content = after.content if after.content else "*無文字內容*"

        if len(before_content) > 1024: before_content = before_content[:1021] + "..."
        if len(after_content) > 1024: after_content = after_content[:1021] + "..."

        embed.add_field(name="修改前", value=before_content, inline=False)
        embed.add_field(name="修改後", value=after_content, inline=False)

        embed.set_footer(text=f"訊息 ID: {before.id}")

        try:
            await log_channel.send(embed=embed)
        except discord.Forbidden:
            pass

    @commands.slash_command(name="set_log_channel", description="設定訊息記錄頻道")
    @commands.has_permissions(administrator=True)
    async def set_log_channel(self, ctx: discord.ApplicationContext, channel: discord.Option(discord.TextChannel, "選擇記錄頻道")):
        self.bot.config["message_logger_channel_id"] = channel.id
        self.bot.save_config()
        await ctx.respond(f"✅ 已將記錄頻道設定為 {channel.mention}", ephemeral=True)

def setup(bot):
    bot.add_cog(MessageLogger(bot))
