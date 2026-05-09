import discord
from discord.ext import tasks, commands
import json
import os
from datetime import datetime

BIRTHDAY_FILE = "birthdays.json"

class BirthdaySystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data = self.load_data()
        self.check_birthdays.start()

    def load_data(self):
        if os.path.exists(BIRTHDAY_FILE):
            try:
                with open(BIRTHDAY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                pass
        return {"channel_id": None, "birthdays": {}, "last_check": None}

    def save_data(self):
        with open(BIRTHDAY_FILE, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4, ensure_ascii=False)

    @tasks.loop(minutes=60)
    async def check_birthdays(self):
        if not self.data["channel_id"]:
            return

        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        
        # 如果今天已經檢查過，就跳過
        if self.data.get("last_check") == today_str:
            return

        channel = self.bot.get_channel(self.data["channel_id"])
        if not channel:
            return

        today_month = now.month
        today_day = now.day
        found_birthday = False

        for user_id_str, bday in self.data["birthdays"].items():
            if bday["month"] == today_month and bday["day"] == today_day:
                try:
                    user = await self.bot.fetch_user(int(user_id_str))
                    if user:
                        age_str = ""
                        if bday.get("year"):
                            age = now.year - bday["year"]
                            age_str = f" 今年 **{age}** 歲了！"
                        
                        embed = discord.Embed(
                            title="🎂 生日快樂！",
                            description=f"今天是 {user.mention} 的生日！{age_str}\n讓我們一起祝他生日快樂！ ✨",
                            color=discord.Color.from_rgb(255, 182, 193)
                        )
                        embed.set_thumbnail(url=user.display_avatar.url)
                        await channel.send(embed=embed)
                        found_birthday = True
                except Exception as e:
                    print(f"Error fetching user {user_id_str} for birthday: {e}")

        self.data["last_check"] = today_str
        self.save_data()

    @check_birthdays.before_loop
    async def before_check_birthdays(self):
        await self.bot.wait_until_ready()

    birthday = discord.SlashCommandGroup("birthday", "生日紀錄系統相關指令")

    @birthday.command(name="set", description="設定您的生日 (年份請使用西元年)")
    async def set_birthday(
        self, 
        ctx: discord.ApplicationContext, 
        date: discord.Option(str, "格式: YYYY-MM-DD 或 MM-DD (例如: 2000-10-01 或 10-01)")
    ):
        # 統一分隔符號
        normalized_date = date.replace("/", "-").replace(".", "-")
        
        parsed_year = None
        parsed_month = None
        parsed_day = None

        # 嘗試解析 YYYY-MM-DD
        try:
            dt = datetime.strptime(normalized_date, "%Y-%m-%d")
            parsed_year = dt.year
            parsed_month = dt.month
            parsed_day = dt.day
        except ValueError:
            # 嘗試解析 MM-DD
            try:
                dt = datetime.strptime(normalized_date, "%m-%d")
                parsed_month = dt.month
                parsed_day = dt.day
            except ValueError:
                return await ctx.respond("❌ 日期格式錯誤！請使用 `YYYY-MM-DD` 或 `MM-DD` (例如: `2000-10-01` 或 `10-01`)。", ephemeral=True)

        self.data["birthdays"][str(ctx.author.id)] = {
            "month": parsed_month,
            "day": parsed_day,
            "year": parsed_year
        }
        self.save_data()
        
        year_str = f"**{parsed_year}** 年 " if parsed_year else ""
        await ctx.respond(f"✅ 已成功設定您的生日為 {year_str}**{parsed_month}** 月 **{parsed_day}** 日！(西元格式)", ephemeral=True)

    @birthday.command(name="remove", description="移除您的生日紀錄")
    async def remove_birthday(self, ctx: discord.ApplicationContext):
        user_id_str = str(ctx.author.id)
        if user_id_str in self.data["birthdays"]:
            del self.data["birthdays"][user_id_str]
            self.save_data()
            await ctx.respond("✅ 已移除您的生日紀錄。", ephemeral=True)
        else:
            await ctx.respond("❌ 您尚未設定生日紀錄。", ephemeral=True)

    @birthday.command(name="setup_channel", description="[管理員] 設定生日祝賀訊息發送的頻道")
    @commands.has_permissions(administrator=True)
    async def setup_channel(
        self, 
        ctx: discord.ApplicationContext, 
        channel: discord.Option(discord.TextChannel, "選擇頻道")
    ):
        self.data["channel_id"] = channel.id
        self.save_data()
        await ctx.respond(f"✅ 生日祝賀頻道已設定為 {channel.mention}。", ephemeral=True)

def setup_birthday_system(bot):
    bot.add_cog(BirthdaySystem(bot))
