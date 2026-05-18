import discord
from discord.ext import commands
import json
import random
import asyncio
import yt_dlp
import os

# --- 全域變數與設定 ---
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)
active_games = {} # 移回模組級別，方便 Autocomplete 存取

# --- Autocomplete 輔助函數 (放在類別外) ---

def get_singer_options(ctx: discord.AutocompleteContext):
    """自動偵測 songs/ 資料夾下的所有藝人 JSON"""
    if not os.path.exists("songs"):
        return []

    choices = []
    user_input = ctx.value.lower()

    all_label = "綜合挑戰 (全藝人)"
    if not user_input or user_input in all_label.lower():
        choices.append(discord.OptionChoice(name=all_label, value="__all__"))

    for filename in os.listdir("songs"):
        if filename.endswith(".json"):
            singer_id = filename.replace(".json", "")
            file_path = f"songs/{filename}"
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    singer_name = data.get("singer", singer_id)
                    if not user_input or user_input in singer_name.lower():
                        choices.append(discord.OptionChoice(name=singer_name, value=singer_id))
            except:
                continue

    return choices[:25]

def get_song_options(ctx: discord.AutocompleteContext):
    """AutoComplete 歌名邏輯"""
    guild_id = ctx.interaction.guild_id
    game_state = active_games.get(guild_id)

    if not game_state or not game_state.get("active"):
        return [discord.OptionChoice(name="目前沒有進行中的遊戲", value="none")]

    singer_id = game_state["singer_id"]
    user_input = ctx.value.lower()
    choices = []

    def collect_from_file(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for song in data['songs']:
                    title = song['title']
                    aliases = song.get('aliases', [])
                    if user_input in title.lower():
                        if not any(c.value == title for c in choices):
                            choices.append(discord.OptionChoice(name=title, value=title))
                        if len(choices) >= 25: return True
                        continue
                    for alias in aliases:
                        if user_input in alias.lower():
                            if not any(c.value == title for c in choices):
                                choices.append(discord.OptionChoice(name=f"{title} ({alias})", value=title))
                            if len(choices) >= 25: return True
                            break
        except:
            pass
        return False

    if singer_id == "__all__":
        for filename in os.listdir("songs"):
            if filename.endswith(".json"):
                if collect_from_file(f"songs/{filename}"):
                    break
    else:
        file_path = f"songs/{singer_id}.json"
        if os.path.exists(file_path):
            collect_from_file(file_path)

    return choices[:25]

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5, actual_start=0):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')
        self.actual_start = actual_start

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False, start_time=None):
        loop = loop or asyncio.get_event_loop()
        try:
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
            if 'entries' in data:
                data = data['entries'][0]

            duration = data.get('duration')

            if start_time is None:
                if duration and duration > 40:
                    actual_start = random.randint(0, int(duration - 35))
                else:
                    actual_start = 0
            else:
                actual_start = start_time

            filename = data['url'] if stream else ytdl.prepare_filename(data)
            ffmpeg_args = {
                'options': f'-vn -ss {actual_start}',
                'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
            }
            return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_args), data=data, actual_start=actual_start)
        except Exception as e:
            raise e

class GuessGame(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command(name="guess", description="開始猜歌挑戰")
    async def guess(
            self,
            ctx: discord.ApplicationContext,
            singer: discord.Option(str, "選擇藝人", autocomplete=get_singer_options)
    ):
        if not ctx.author.voice:
            return await ctx.respond("你必須先加入語音頻道！", ephemeral=True)

        guild_id = ctx.guild_id
        if active_games.get(guild_id, {}).get("active"):
            return await ctx.respond("目前已有遊戲正在進行中！", ephemeral=True)

        all_songs = []
        singer_name = ""

        if singer == "__all__":
            singer_name = "綜合挑戰"
            for filename in os.listdir("songs"):
                if filename.endswith(".json"):
                    try:
                        with open(f"songs/{filename}", "r", encoding="utf-8") as f:
                            data = json.load(f)
                            for s in data['songs']:
                                s['singer_origin'] = data.get('singer', filename.replace(".json", ""))
                                all_songs.append(s)
                    except:
                        continue
            if not all_songs:
                return await ctx.respond("題庫中沒有任何歌曲！", ephemeral=True)
            current_song = random.choice(all_songs)
        else:
            file_path = f"songs/{singer}.json"
            if not os.path.exists(file_path):
                return await ctx.respond(f"找不到藝人 `{singer}` 的題庫。", ephemeral=True)

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    song_data = json.load(f)
                    all_songs = song_data['songs']
                    singer_name = song_data['singer']
                    current_song = random.choice(all_songs)
            except Exception as e:
                return await ctx.respond(f"題庫檔案 `{singer}.json` 讀取失敗：{e}", ephemeral=True)

        active_games[guild_id] = {
            "singer_id": singer,
            "current_song": current_song,
            "active": True,
            "singer_name": singer_name
        }

        await ctx.respond(f"🎵 **{singer_name}** 猜歌挑戰開始！\n請聽音樂並使用 `/answer` 回答。")

        vc = None
        try:
            if ctx.voice_client:
                vc = ctx.voice_client
                if vc.channel != ctx.author.voice.channel:
                    await vc.move_to(ctx.author.voice.channel)
            else:
                vc = await ctx.author.voice.channel.connect()

            await ctx.guild.change_voice_state(channel=ctx.author.voice.channel, self_deaf=True)

            player = await YTDLSource.from_url(current_song['url'], loop=self.bot.loop, stream=True, start_time=current_song.get("start_time"))
            vc.play(player)

            for _ in range(30):
                await asyncio.sleep(1)
                if not active_games.get(guild_id, {}).get("active"):
                    break

            if active_games.get(guild_id, {}).get("active"):
                await ctx.send(f"⏰ 時間到！這首歌是：**{current_song['title']}** (來自: {current_song.get('singer_origin', singer_name)})")
                active_games[guild_id]["active"] = False
        except Exception as e:
            print(f"Error in guess: {e}")
            await ctx.send(f"⚠️ 播放出錯：影片可能暫時無法存取。")
            if guild_id in active_games: active_games[guild_id]["active"] = False
        finally:
            if vc and vc.is_connected(): await vc.disconnect()

    @discord.slash_command(name="answer", description="回答猜歌答案")
    async def answer(
            self,
            ctx: discord.ApplicationContext,
            song_name: discord.Option(str, "選擇歌名", autocomplete=get_song_options)
    ):
        guild_id = ctx.guild_id
        game_state = active_games.get(guild_id)
        if not game_state or not game_state.get("active"):
            return await ctx.respond("目前沒有進行中的遊戲。", ephemeral=True)

        if not ctx.author.voice or not ctx.voice_client or ctx.author.voice.channel != ctx.voice_client.channel:
            return await ctx.respond("您必須在機器人所在的語音頻道中才能回答！", ephemeral=True)

        correct_song = game_state["current_song"]
        is_correct = (song_name.lower() == correct_song["title"].lower()) or \
                     (song_name.lower() in [a.lower() for a in correct_song.get("aliases", [])])

        if is_correct:
            game_state["active"] = False
            origin = f" (來自: {correct_song.get('singer_origin', game_state['singer_name'])})" if game_state['singer_id'] == "__all__" else ""
            await ctx.respond(f"🎉 恭喜 {ctx.author.mention} 答對了！\n正確答案：**{correct_song['title']}**{origin}")
            if ctx.voice_client: ctx.voice_client.stop()
        else:
            await ctx.respond(f"❌ 答錯囉！", ephemeral=True)

def setup(bot):
    bot.add_cog(GuessGame(bot))
