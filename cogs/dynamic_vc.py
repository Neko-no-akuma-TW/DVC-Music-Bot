import discord
from discord.ext import commands

class DynamicVoice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        channels = self.bot.config.get("dynamic_channels", {})
        made_changes = False

        # 處理空頻道的自動刪除
        if before.channel and str(before.channel.id) in channels and len(before.channel.members) == 0:
            try:
                await before.channel.delete(reason="Dynamic channel empty")
                del channels[str(before.channel.id)]
                made_changes = True
            except discord.NotFound:
                # 頻道可能已經被手動刪除
                del channels[str(before.channel.id)]
                made_changes = True
            except discord.Forbidden:
                print(f"Permission denied: Could not delete channel {before.channel.id}")

        # 處理新頻道的創建
        creator_id = self.bot.config.get("creator_channel_id")
        if after.channel and after.channel.id == creator_id:
            category = after.channel.category
            name = f"{member.display_name} 的語音頻道"
            try:
                new_channel = await category.create_voice_channel(name=name, reason=f"{member.name} created it.")
                await member.move_to(new_channel)
                channels[str(new_channel.id)] = {"owner_id": member.id, "manager_ids": []}
                made_changes = True
            except discord.Forbidden:
                print("Permission denied: Could not create or move member to new voice channel")

        if made_changes:
            self.bot.config["dynamic_channels"] = channels
            self.bot.save_config()

    @discord.slash_command(name="info", description="顯示目前動態頻道的資訊")
    async def channel_info(self, ctx: discord.ApplicationContext):
        vc = ctx.author.voice.channel if ctx.author.voice else None
        if not vc: return await ctx.respond("您必須在一個語音頻道中。", ephemeral=True)

        vc_id_str = str(vc.id)
        channels = self.bot.config.get("dynamic_channels", {})
        if vc_id_str not in channels:
            return await ctx.respond("這不是一個動態語音頻道。", ephemeral=True)

        info = channels[vc_id_str]
        owner = await self.bot.fetch_user(info['owner_id'])
        managers = [await self.bot.fetch_user(uid) for uid in info.get('manager_ids', [])]

        embed = discord.Embed(title=f"頻道資訊 - {vc.name}", color=discord.Color.blue())
        embed.add_field(name="擁有者", value=owner.mention, inline=False)
        embed.add_field(name="管理員", value='\n'.join([m.mention for m in managers]) if managers else "無", inline=False)
        embed.add_field(name="目前人數", value=f"{len(vc.members)} 人", inline=False)
        await ctx.respond(embed=embed, ephemeral=True)

    @discord.slash_command(name="rename", description="[擁有者/管理員] 重新命名頻道")
    async def rename_channel(self, ctx: discord.ApplicationContext, name: discord.Option(str, "新的頻道名稱", required=True)):
        vc = ctx.author.voice.channel if ctx.author.voice else None
        if not vc: return await ctx.respond("您必須在一個語音頻道中。", ephemeral=True)

        vc_id_str = str(vc.id)
        channels = self.bot.config.get("dynamic_channels", {})
        if vc_id_str in channels:
            info = channels[vc_id_str]
            is_owner = ctx.author.id == info.get("owner_id")
            is_manager = ctx.author.id in info.get("manager_ids", [])
            if is_owner or is_manager:
                await vc.edit(name=name, reason=f"By {ctx.author.name}")
                await ctx.respond(f"頻道名稱已更改為「{name}」。", ephemeral=True)
            else:
                await ctx.respond("您沒有權限重新命名此頻道。", ephemeral=True)
        else:
            await ctx.respond("這不是一個動態語音頻道。", ephemeral=True)

    @discord.slash_command(name="add_manager", description="[限擁有者] 新增一位頻道管理員")
    async def add_manager(self, ctx: discord.ApplicationContext, user: discord.Option(discord.Member, "要新增的管理員", required=True)):
        vc = ctx.author.voice.channel if ctx.author.voice else None
        if not vc: return await ctx.respond("您必須在一個語音頻道中。", ephemeral=True)

        vc_id_str = str(vc.id)
        channels = self.bot.config.get("dynamic_channels", {})
        if vc_id_str in channels and channels[vc_id_str].get("owner_id") == ctx.author.id:
            managers = channels[vc_id_str].setdefault("manager_ids", [])
            if user.id in managers: return await ctx.respond(f"{user.mention} 已經是管理員了。", ephemeral=True)
            managers.append(user.id)
            self.bot.save_config()
            await ctx.respond(f"已新增 {user.mention} 為此頻道的管理員。", ephemeral=False)
        else:
            await ctx.respond("只有頻道擁有者才能新增管理員。", ephemeral=True)

    @discord.slash_command(name="remove_manager", description="[限擁有者] 移除一位頻道管理員")
    async def remove_manager(self, ctx: discord.ApplicationContext, user: discord.Option(discord.Member, "要移除的管理員", required=True)):
        vc = ctx.author.voice.channel if ctx.author.voice else None
        if not vc: return await ctx.respond("您必須在一個語音頻道中。", ephemeral=True)

        vc_id_str = str(vc.id)
        channels = self.bot.config.get("dynamic_channels", {})
        if vc_id_str in channels and channels[vc_id_str].get("owner_id") == ctx.author.id:
            managers = channels[vc_id_str].get("manager_ids", [])
            if user.id not in managers: return await ctx.respond(f"{user.mention} 不是管理員。", ephemeral=True)
            managers.remove(user.id)
            self.bot.save_config()
            await ctx.respond(f"已將 {user.mention} 從管理員中移除。", ephemeral=False)
        else:
            await ctx.respond("只有頻道擁有者才能移除管理員。", ephemeral=True)

    @discord.slash_command(name="transfer", description="[限擁有者] 將頻道擁有權完全轉移")
    async def transfer_ownership(self, ctx: discord.ApplicationContext, new_owner: discord.Option(discord.Member, "新的唯一擁有者", required=True)):
        vc = ctx.author.voice.channel if ctx.author.voice else None
        if not vc: return await ctx.respond("您必須在一個語音頻道中。", ephemeral=True)

        vc_id_str = str(vc.id)
        channels = self.bot.config.get("dynamic_channels", {})
        if vc_id_str in channels and channels[vc_id_str].get("owner_id") == ctx.author.id:
            channels[vc_id_str]["owner_id"] = new_owner.id
            channels[vc_id_str]["manager_ids"] = []
            self.bot.save_config()
            await ctx.respond(f"擁有權已轉移給 {new_owner.mention}。管理員列表已清空。", ephemeral=False)
        else:
            await ctx.respond("只有頻道擁有者才能轉移擁有權。", ephemeral=True)

def setup(bot):
    bot.add_cog(DynamicVoice(bot))
