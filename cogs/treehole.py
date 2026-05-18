import discord
from discord.ext import commands, tasks
import asyncio

class Treehole(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    def get_channel_id(self):
        return self.bot.config.get("treehole_channel_id", 1505202112529694751)

    @tasks.loop(hours=1)
    async def _automatically_check_tree_hole(self):
        channel = await self.bot.fetch_channel(self.get_channel_id())
        threads = channel.threads

        violance_threads = []
        for thread in threads:
            if (thread.name.lower() != thread.owner.name) and (thread.name != "樹洞區貼文格式以及規則說明"):
                violance_threads.append(thread)

        for violance_thread in violance_threads:
            await violance_thread.edit(name=violance_thread.owner.name, reason="不符合規定的樹洞")
            await violance_thread.send(f"{violance_thread.owner.mention}\n本討論串與您現在使用者名稱並不相符，已經自動幫您調整。")

        new_channel = await self.bot.fetch_channel(self.get_channel_id())
        threads_new = new_channel.threads

        threads_name = [k.name.lower() for k in threads_new]
        seen = set()
        duplicates = set()
        for name in threads_name:
            if name in seen:
                duplicates.add(name)
            else:
                seen.add(name)


        for thread in threads:
            if thread.name.lower() in duplicates:
                duplicates.remove(thread.name.lower())
                await thread.delete()

    @discord.slash_command(name="check_tree_hole_name", description="檢查樹洞區重複名稱之貼文")
    @commands.has_permissions(administrator=True)
    async def check_tree_hole_name(self, ctx: discord.ApplicationContext):
        channel = await self.bot.fetch_channel(self.get_channel_id())
        threads = channel.threads
        threads_name = [k.name.lower() for k in threads]
        seen = set()
        duplicates = set()
        for name in threads_name:
            if name in seen:
                duplicates.add(name)
            else:
                seen.add(name)

        await ctx.respond("沒有重複名稱的討論串" if list(duplicates) == [] else ("重複的有" + "\n".join(list(duplicates))), ephemeral=True)

        violance_threads = []
        for thread in threads:
            if (thread.name.lower() != thread.owner.name) and (thread.name != "樹洞區貼文格式以及規則說明"):
                violance_threads.append(thread)
        violance_threads_mention = [k.mention for k in violance_threads]
        await ctx.respond("沒有不符合的討論串" if list(violance_threads_mention) == [] else ("不符合的有" + "\n".join(list(violance_threads_mention))), ephemeral=True)

        for violance_thread in violance_threads:
            await violance_thread.edit(name=violance_thread.owner.name, reason="不符合規定的樹洞")
            await violance_thread.send(f"{violance_thread.owner.mention}\n本討論串與您現在使用者名稱並不相符，已經自動幫您調整。")

    @commands.Cog.listener()
    async def on_thread_create(self, thread: discord.Thread):
        channel_id = self.get_channel_id()
        rules_id = self.bot.config.get("treehole_rules_id", 1505202438288834700)
        if (thread.parent.id == channel_id) and (thread.name != thread.owner.name):
            await thread.send(f"{thread.owner.mention} 系統檢測到您的樹洞頻道名稱與您的使用者名稱不相符，並不符合樹洞區規定，請您詳閱規定後重新創建。本頻道將於30秒後自動移除。\n\n樹洞區規則：<#{rules_id}>\n\n如果您認為這個自動化管理機制運行有誤，請向管理團隊Neko反映。", allowed_mentions=discord.AllowedMentions.all())
            await asyncio.sleep(30)
            await thread.delete()

    @commands.Cog.listener()
    async def on_ready(self):
        if not self._automatically_check_tree_hole.is_running():
            self._automatically_check_tree_hole.start()

def setup(bot):
    bot.add_cog(Treehole(bot))
