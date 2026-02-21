import discord
import json
from dotenv import load_dotenv
import os
from guess_game import setup_guess_commands

# --- 全域設定 ---
load_dotenv()
bot = discord.Bot(intents=discord.Intents.all(), allowed_mentions=discord.AllowedMentions.none())
setup_guess_commands(bot)
CONFIG_FILE = "voice_channel.json"
bot_config = {} # 用於快取設定的記憶體變數

# --- 輔助函式 ---
def load_config():
    global bot_config
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            bot_config = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        print(f"Warning: {CONFIG_FILE} not found or is invalid. Creating a default config.")
        bot_config = {
            "creator_channel_id": 0,
            "dynamic_channels": {}
        }
        save_config()

def save_config():
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(bot_config, f, indent=4)

# --- Bot 事件 ---
@bot.event
async def on_ready():
    load_config()
    print(f"Bot is online as {bot.user.name}")
    print(f"Loaded {len(bot_config.get('dynamic_channels', {}))} dynamic channels.")
    if bot_config.get("creator_channel_id") == 0:
        print("CRITICAL: 'creator_channel_id' is not set in voice_channel.json!")

@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    roles = after.roles

    for role in roles:
        if role.id == 1442868687559196774:
            await after.kick(reason="此使用者疑似為自動化程式，因此遭到了移除")

@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    channels = bot_config.get("dynamic_channels", {})
    made_changes = False

    if before.channel and str(before.channel.id) in channels and len(before.channel.members) == 0:
        print(f"Deleting empty channel: {before.channel.name}")
        await before.channel.delete(reason="Dynamic channel empty")
        del channels[str(before.channel.id)]
        made_changes = True

    if after.channel and after.channel.id == bot_config.get("creator_channel_id"):
        category = after.channel.category
        name = f"{member.display_name} 的語音頻道"
        print(f"Creating new channel for {member.display_name}")
        new_channel = await category.create_voice_channel(name=name, reason=f"{member.name} created it.")
        await member.move_to(new_channel)
        channels[str(new_channel.id)] = {"owner_id": member.id, "manager_ids": []}
        made_changes = True

    if made_changes:
        save_config()

@bot.event
async def on_message(message: discord.Message):
    if (message.author.bot or message.channel.id != 1310558640230498334):
        return
    if ("x.com" in message.content) or ("twitter.com" in message.content):
        new_content = message.content.replace("x.com", "fixvx.com")
        new_content = new_content.replace("twitter.com", "fixvx.com")
        n_message = await message.channel.send(new_content + f"\n作者：{message.author.mention}")
        await message.delete()
        await n_message.add_reaction("❤️")



# --- Bot 指令 ---
@bot.slash_command(name="info", description="顯示目前動態頻道的資訊")
async def channel_info(ctx: discord.ApplicationContext):
    vc = ctx.author.voice.channel if ctx.author.voice else None
    if not vc: return await ctx.respond("您必須在一個語音頻道中。", ephemeral=True)

    vc_id_str = str(vc.id)
    channels = bot_config.get("dynamic_channels", {})
    if vc_id_str not in channels:
        return await ctx.respond("這不是一個動態語音頻道。", ephemeral=True)

    info = channels[vc_id_str]
    owner = await bot.fetch_user(info['owner_id'])
    managers = [await bot.fetch_user(uid) for uid in info.get('manager_ids', [])]

    embed = discord.Embed(title=f"頻道資訊 - {vc.name}", color=discord.Color.blue())
    embed.add_field(name="擁有者", value=owner.mention, inline=False)
    embed.add_field(name="管理員", value='\n'.join([m.mention for m in managers]) if managers else "無", inline=False)
    embed.add_field(name="目前人數", value=f"{len(vc.members)} 人", inline=False)
    await ctx.respond(embed=embed, ephemeral=True)

@bot.slash_command(name="rename", description="[擁有者/管理員] 重新命名頻道")
async def rename_channel(ctx: discord.ApplicationContext, name: discord.Option(str, "新的頻道名稱", required=True)):
    vc = ctx.author.voice.channel if ctx.author.voice else None
    if not vc: return await ctx.respond("您必須在一個語音頻道中。", ephemeral=True)

    vc_id_str = str(vc.id)
    channels = bot_config.get("dynamic_channels", {})
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

@bot.slash_command(name="add_manager", description="[限擁有者] 新增一位頻道管理員")
async def add_manager(ctx: discord.ApplicationContext, user: discord.Option(discord.Member, "要新增的管理員", required=True)):
    vc = ctx.author.voice.channel if ctx.author.voice else None
    if not vc: return await ctx.respond("您必須在一個語音頻道中。", ephemeral=True)

    vc_id_str = str(vc.id)
    channels = bot_config.get("dynamic_channels", {})
    if vc_id_str in channels and channels[vc_id_str].get("owner_id") == ctx.author.id:
        managers = channels[vc_id_str].setdefault("manager_ids", [])
        if user.id in managers: return await ctx.respond(f"{user.mention} 已經是管理員了。", ephemeral=True)
        
        managers.append(user.id)
        save_config()
        await ctx.respond(f"已新增 {user.mention} 為此頻道的管理員。", ephemeral=False)
    else:
        await ctx.respond("只有頻道擁有者才能新增管理員。", ephemeral=True)

@bot.slash_command(name="remove_manager", description="[限擁有者] 移除一位頻道管理員")
async def remove_manager(ctx: discord.ApplicationContext, user: discord.Option(discord.Member, "要移除的管理員", required=True)):
    vc = ctx.author.voice.channel if ctx.author.voice else None
    if not vc: return await ctx.respond("您必須在一個語音頻道中。", ephemeral=True)

    vc_id_str = str(vc.id)
    channels = bot_config.get("dynamic_channels", {})
    if vc_id_str in channels and channels[vc_id_str].get("owner_id") == ctx.author.id:
        managers = channels[vc_id_str].get("manager_ids", [])
        if user.id not in managers: return await ctx.respond(f"{user.mention} 不是管理員。", ephemeral=True)

        managers.remove(user.id)
        save_config()
        await ctx.respond(f"已將 {user.mention} 從管理員中移除。", ephemeral=False)
    else:
        await ctx.respond("只有頻道擁有者才能移除管理員。", ephemeral=True)

@bot.slash_command(name="transfer", description="[限擁有者] 將頻道擁有權完全轉移")
async def transfer_ownership(ctx: discord.ApplicationContext, new_owner: discord.Option(discord.Member, "新的唯一擁有者", required=True)):
    vc = ctx.author.voice.channel if ctx.author.voice else None
    if not vc: return await ctx.respond("您必須在一個語音頻道中。", ephemeral=True)

    vc_id_str = str(vc.id)
    channels = bot_config.get("dynamic_channels", {})
    if vc_id_str in channels and channels[vc_id_str].get("owner_id") == ctx.author.id:
        channels[vc_id_str]["owner_id"] = new_owner.id
        channels[vc_id_str]["manager_ids"] = [] # 清空管理員列表
        save_config()
        await ctx.respond(f"擁有權已轉移給 {new_owner.mention}。管理員列表已清空。", ephemeral=False)
    else:
        await ctx.respond("只有頻道擁有者才能轉移擁有權。", ephemeral=True)

bot.run(os.environ["TOKEN"])
