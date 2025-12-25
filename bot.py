import discord
from discord.ext import commands, tasks
import aiohttp
import random
import os
from dotenv import load_dotenv

# تحميل المتغيرات البيئية
load_dotenv()

# إعداد البوت
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# API endpoint لـ ScriptBlox
SCRIPTBLOX_API = "https://scriptblox.com/api/script/fetch"

class ScriptBot:
    def __init__(self):
        self.scripts_cache = []
        self.last_page = 1
        
    async def fetch_scripts(self, page=1, max_results=50):
        """جلب السكربتات من ScriptBlox API"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{SCRIPTBLOX_API}?page={page}&max={max_results}"
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('result', {}).get('scripts', [])
                    else:
                        print(f"خطأ في جلب البيانات: {response.status}")
                        return []
        except Exception as e:
            print(f"خطأ: {e}")
            return []
    
    async def get_random_script(self):
        """الحصول على سكربت عشوائي"""
        # جلب صفحة عشوائية من 1 إلى 100
        random_page = random.randint(1, 100)
        scripts = await self.fetch_scripts(page=random_page, max_results=50)
        
        if scripts:
            return random.choice(scripts)
        return None
    
    def format_script_embed(self, script_data):
        """تنسيق السكربت كـ Embed في Discord"""
        embed = discord.Embed(
            title=script_data.get('title', 'بدون عنوان'),
            color=discord.Color.blue(),
            url=f"https://scriptblox.com/script/{script_data.get('slug', '')}"
        )
        
        # اسم اللعبة/الماب
        game = script_data.get('game', {})
        game_name = game.get('name', 'غير محدد')
        embed.add_field(name="🎮 اللعبة/الماب", value=game_name, inline=True)
        
        # المشاهدات
        views = script_data.get('views', 0)
        embed.add_field(name="👁️ المشاهدات", value=f"{views:,}", inline=True)
        
        # نوع السكربت
        script_type = "🔑 يحتاج مفتاح" if script_data.get('key', False) else "✅ مجاني"
        embed.add_field(name="النوع", value=script_type, inline=True)
        
        # صورة اللعبة
        image_url = script_data.get('image', '')
        if image_url:
            if not image_url.startswith('http'):
                image_url = f"https://scriptblox.com{image_url}"
            embed.set_thumbnail(url=image_url)
        
        # إضافة السكربت
        script_code = script_data.get('script', 'غير متوفر')
        if len(script_code) > 1024:
            script_code = script_code[:1021] + "..."
        embed.add_field(name="📜 السكربت", value=f"```lua\n{script_code}\n```", inline=False)
        
        # معلومات إضافية
        embed.set_footer(text=f"ScriptBlox • ID: {script_data.get('_id', 'N/A')}")
        
        return embed

# إنشاء instance من ScriptBot
script_bot = ScriptBot()

@bot.event
async def on_ready():
    print(f'✅ البوت جاهز! تم تسجيل الدخول كـ {bot.user}')
    print(f'🔗 رابط دعوة البوت: https://discord.com/api/oauth2/authorize?client_id={bot.user.id}&permissions=274877975552&scope=bot')
    # بدء المهمة التلقائية
    if not auto_send_script.is_running():
        auto_send_script.start()

@bot.command(name='script')
async def get_script(ctx):
    """الحصول على سكربت عشوائي"""
    await ctx.send("⏳ جاري البحث عن سكربت عشوائي...")
    
    script = await script_bot.get_random_script()
    
    if script:
        embed = script_bot.format_script_embed(script)
        await ctx.send(embed=embed)
    else:
        await ctx.send("❌ فشل في جلب السكربت. حاول مرة أخرى.")

@bot.command(name='autoscript')
@commands.has_permissions(administrator=True)
async def toggle_auto_script(ctx, channel: discord.TextChannel = None, interval: int = 3600):
    """
    تفعيل/إيقاف إرسال السكربتات التلقائي
    الاستخدام: !autoscript #channel 3600
    interval بالثواني (افتراضي: 3600 = ساعة واحدة)
    """
    global auto_channel, auto_interval
    
    if channel is None:
        channel = ctx.channel
    
    auto_channel = channel
    auto_interval = interval
    
    if auto_send_script.is_running():
        auto_send_script.cancel()
        await ctx.send(f"✅ تم إيقاف الإرسال التلقائي")
    else:
        auto_send_script.change_interval(seconds=interval)
        auto_send_script.start()
        await ctx.send(f"✅ تم تفعيل الإرسال التلقائي في {channel.mention} كل {interval} ثانية")

@bot.command(name='help_bot')
async def help_command(ctx):
    """عرض قائمة الأوامر"""
    embed = discord.Embed(
        title="📚 قائمة أوامر البوت",
        description="بوت جلب سكربتات Roblox من ScriptBlox",
        color=discord.Color.green()
    )
    
    embed.add_field(
        name="!script",
        value="الحصول على سكربت عشوائي من ScriptBlox",
        inline=False
    )
    
    embed.add_field(
        name="!autoscript #channel 3600",
        value="تفعيل/إيقاف الإرسال التلقائي (للمسؤولين فقط)\nالرقم هو الفترة بالثواني",
        inline=False
    )
    
    embed.add_field(
        name="!help_bot",
        value="عرض هذه القائمة",
        inline=False
    )
    
    await ctx.send(embed=embed)

# متغيرات للإرسال التلقائي
auto_channel = None
auto_interval = 3600  # ساعة واحدة افتراضياً

@tasks.loop(seconds=3600)
async def auto_send_script():
    """إرسال سكربت تلقائياً كل فترة محددة"""
    if auto_channel:
        script = await script_bot.get_random_script()
        if script:
            embed = script_bot.format_script_embed(script)
            await auto_channel.send("🎲 **سكربت عشوائي جديد!**", embed=embed)

@auto_send_script.before_loop
async def before_auto_send():
    await bot.wait_until_ready()

# تشغيل البوت
if __name__ == "__main__":
    TOKEN = os.getenv('DISCORD_TOKEN')
    if not TOKEN:
        print("❌ خطأ: لم يتم العثور على DISCORD_TOKEN في ملف .env")
        print("يرجى إنشاء ملف .env وإضافة: DISCORD_TOKEN=MTQ1Mzc4NDY5MzQyOTUwMTk1Mg.GIEtj2.gVJluy0pstoxSyl0yWDqRSv3UPzR-2DYYzWVvA")
    else:
        bot.run(TOKEN)
