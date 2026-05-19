import discord
from discord.ext import commands
import datetime
import io

class MessageLogger(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _get_log_channel(self, guild):
        """從全域設定獲取記錄頻道"""
        channel_id = self.bot.config.get("message_logger_channel_id", 0)
        return guild.get_channel(channel_id)

    async def _get_attachment_files(self, attachments):
        """將附件轉換為 discord.File 列表"""
        files = []
        for attachment in attachments:
            try:
                # 限制檔案大小，避免超過 Discord 機器人上傳限制 (通常為 8MB)
                if attachment.size > 8 * 1024 * 1024:
                    continue
                
                fp = io.BytesIO()
                await attachment.save(fp)
                fp.seek(0)
                files.append(discord.File(fp, filename=attachment.filename))
            except Exception as e:
                print(f"Error saving attachment: {e}")
        return files

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        # 排除在 Twitter 修正頻道中因為自動轉換連結而產生的刪除記錄
        fix_vx_id = self.bot.config.get("fix_vx_channel_id")
        if message.channel.id == fix_vx_id:
            if message.content and ("x.com" in message.content or "twitter.com" in message.content):
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

        files = []
        if message.attachments:
            files = await self._get_attachment_files(message.attachments)
            attachment_names = ", ".join([a.filename for a in message.attachments])
            embed.add_field(name="附件 (已保存)", value=attachment_names, inline=False)
            
            # 如果第一個附件是圖片，將其設為 Embed 預覽圖
            if message.attachments[0].content_type and message.attachments[0].content_type.startswith("image"):
                embed.set_image(url=f"attachment://{message.attachments[0].filename}")

        embed.set_footer(text=f"訊息 ID: {message.id}")
        
        try:
            await log_channel.send(embed=embed, files=files)
        except discord.Forbidden:
            pass
        except Exception as e:
            print(f"Failed to send delete log: {e}")

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot or not before.guild:
            return

        # 檢查內容是否真的有變動，或者附件是否有減少
        if before.content == after.content and len(before.attachments) <= len(after.attachments):
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

        # 處理被移除的附件
        removed_attachments = [a for a in before.attachments if a not in after.attachments]
        files = []
        if removed_attachments:
            files = await self._get_attachment_files(removed_attachments)
            attachment_names = ", ".join([a.filename for a in removed_attachments])
            embed.add_field(name="被移除的附件 (已保存)", value=attachment_names, inline=False)
            
            if removed_attachments[0].content_type and removed_attachments[0].content_type.startswith("image"):
                embed.set_image(url=f"attachment://{removed_attachments[0].filename}")

        embed.set_footer(text=f"訊息 ID: {before.id}")

        try:
            await log_channel.send(embed=embed, files=files)
        except discord.Forbidden:
            pass
        except Exception as e:
            print(f"Failed to send edit log: {e}")

    @commands.slash_command(name="set_log_channel", description="設定訊息記錄頻道")
    @commands.has_permissions(administrator=True)
    async def set_log_channel(self, ctx: discord.ApplicationContext, channel: discord.Option(discord.TextChannel, "選擇記錄頻道")):
        self.bot.config["message_logger_channel_id"] = channel.id
        self.bot.save_config()
        await ctx.respond(f"✅ 已將記錄頻道設定為 {channel.mention}", ephemeral=True)

def setup(bot):
    bot.add_cog(MessageLogger(bot))
