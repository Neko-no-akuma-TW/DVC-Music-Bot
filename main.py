import discord
import json
import os
from discord.ext import commands
from dotenv import load_dotenv

# --- 全域設定 ---
load_dotenv()

class MyBot(discord.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.CONFIG_FILE = "config.json"
        self.config = self.load_config()
        
        # 啟動前載入插件，確保斜線指令正確同步
        self.load_all_extensions()

    def load_config(self):
        try:
            if os.path.exists(self.CONFIG_FILE):
                with open(self.CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
        
        return {
            "creator_channel_id": 0,
            "dynamic_channels": {},
            "message_logger_channel_id": 0,
            "treehole_channel_id": 1505202112529694751,
            "treehole_rules_id": 1505202438288834700,
            "fix_vx_channel_id": 1310558640230498334,
            "auto_kick_role_id": 1442868687559196774
        }

    def save_config(self):
        try:
            with open(self.CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving config: {e}")

    def load_all_extensions(self):
        print("Loading extensions...")
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py"):
                try:
                    self.load_extension(f"cogs.{filename[:-3]}")
                    print(f"Loaded extension: {filename}")
                except Exception as e:
                    print(f"Failed to load extension {filename}: {e}")

bot = MyBot(intents=discord.Intents.all(), allowed_mentions=discord.AllowedMentions.none())

# --- Cog 管理指令 ---
cog_admin = discord.SlashCommandGroup("cog", "插件管理指令")

@cog_admin.command(name="load", description="載入插件")
@commands.has_permissions(administrator=True)
async def load_cog(ctx: discord.ApplicationContext, name: discord.Option(str, "插件名稱 (例如: guess_game)")):
    try:
        bot.load_extension(f"cogs.{name}")
        await ctx.respond(f"✅ 已載入插件: `{name}`", ephemeral=True)
    except Exception as e:
        await ctx.respond(f"❌ 載入失敗: `{e}`", ephemeral=True)

@cog_admin.command(name="unload", description="卸載插件")
@commands.has_permissions(administrator=True)
async def unload_cog(ctx: discord.ApplicationContext, name: discord.Option(str, "插件名稱")):
    try:
        bot.unload_extension(f"cogs.{name}")
        await ctx.respond(f"✅ 已卸載插件: `{name}`", ephemeral=True)
    except Exception as e:
        await ctx.respond(f"❌ 卸載失敗: `{e}`", ephemeral=True)

@cog_admin.command(name="reload", description="重新載入插件")
@commands.has_permissions(administrator=True)
async def reload_cog(ctx: discord.ApplicationContext, name: discord.Option(str, "插件名稱")):
    try:
        bot.reload_extension(f"cogs.{name}")
        await ctx.respond(f"✅ 已重新載入插件: `{name}`", ephemeral=True)
    except Exception as e:
        await ctx.respond(f"❌ 重新載入失敗: `{e}`", ephemeral=True)

bot.add_application_command(cog_admin)

# --- 設定指令 ---
config_cmd = discord.SlashCommandGroup("config", "全域設定指令")

@config_cmd.command(name="set_creator_vc", description="設定動態頻道創建點")
@commands.has_permissions(administrator=True)
async def set_creator_vc(ctx: discord.ApplicationContext, channel: discord.Option(discord.VoiceChannel, "選擇頻道")):
    bot.config["creator_channel_id"] = channel.id
    bot.save_config()
    await ctx.respond(f"✅ 動態頻道創建點已設定為 {channel.mention}", ephemeral=True)

@config_cmd.command(name="set_fix_vx_channel", description="設定自動修正 Twitter 連結的頻道")
@commands.has_permissions(administrator=True)
async def set_fix_vx(ctx: discord.ApplicationContext, channel: discord.Option(discord.TextChannel, "選擇頻道")):
    bot.config["fix_vx_channel_id"] = channel.id
    bot.save_config()
    await ctx.respond(f"✅ Twitter 修正頻道已設定為 {channel.mention}", ephemeral=True)

bot.add_application_command(config_cmd)

# --- 基本事件 ---
@bot.event
async def on_ready():
    print(f"Bot is online as {bot.user.name}")

@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    role_id = bot.config.get("auto_kick_role_id")
    if role_id and any(role.id == role_id for role in after.roles):
        try:
            await after.kick(reason="此使用者疑似為自動化程式，因此遭到了移除")
        except:
            pass

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    
    fix_vx_id = bot.config.get("fix_vx_channel_id")
    if message.channel.id == fix_vx_id:
        if ("x.com" in message.content) or ("twitter.com" in message.content):
            new_content = message.content.replace("x.com", "fixvx.com").replace("twitter.com", "fixvx.com")
            n_message = await message.channel.send(new_content + f"\n作者：{message.author.mention}")
            await message.delete()
            await n_message.add_reaction("❤️")

bot.run(os.environ["TOKEN"])
