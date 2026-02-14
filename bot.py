import asyncio
import logging
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from database import init_db, add_or_update_match, get_pending_matches, mark_as_notified
from scraper import scrape_all_matches

load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler()

@dp.message(Command("start"))
async def cmd_start(message: Message):
    global ADMIN_CHAT_ID
    if not ADMIN_CHAT_ID:
        ADMIN_CHAT_ID = str(message.chat.id)
        await message.answer(f"✅ Bot bağlandı!\n📍 45 dakikada bir kontrol edeceğim.\n⚠️ Maç başladıktan 120 dk sonra özet bildirimi atarım.")
    else:
        await message.answer("⚽ Takip sistemi aktif. Maç bitiminden 2 saat sonra özet kontrolü yapıyorum.")

async def discovery_job():
    """Yeni maçları keşfetmek için 45 dakikada bir çalışır."""
    if not ADMIN_CHAT_ID: return
    logging.info("🔍 [Keşif] Yeni maçlar aranıyor (45dk periyot)...")
    found_matches = await scrape_all_matches()
    for m in found_matches:
        add_or_update_match(m['match_id'], m['teams'], m['start_time'])
    logging.info(f"🔍 [Keşif] {len(found_matches)} maç güncellendi.")

async def summary_check_job():
    """Süresi dolan maçların özetlerini 5 dakikada bir kontrol eder."""
    if not ADMIN_CHAT_ID: return
    
    pending_ids = get_pending_matches()
    if not pending_ids:
        return

    logging.info(f"🚀 [Takip] {len(pending_ids)} maç için özet kontrolü yapılıyor (5dk periyot)...")
    
    # Sayfayı tara ve linkleri al
    found_matches = await scrape_all_matches()
    
    for mid in pending_ids:
        match_data = next((x for x in found_matches if x['match_id'] == mid), None)
        
        if match_data and match_data['url']:
            text = (
                f"🎉 **Özet Yüklendi!**\n\n"
                f"⚽️ **Maç:** {match_data['teams']}\n\n"
                f"🍿 **Keyifli seyirler!**"
            )
            try:
                await bot.send_message(ADMIN_CHAT_ID, text, parse_mode="Markdown")
                mark_as_notified(mid)
                logging.info(f"✅ BİLDİRİLDİ: {match_data['teams']}")
            except Exception as e:
                logging.error(f"❌ Telegram hatası: {e}")

async def main():
    init_db()
    
    # 1. Yeni maçları bulma: 45 dakikada bir
    scheduler.add_job(discovery_job, "interval", minutes=45)
    
    # 2. Özet kontrolü: 5 dakikada bir
    scheduler.add_job(summary_check_job, "interval", minutes=5)
    
    # Başlangıçta ikisini de bir kez çalıştır
    await discovery_job()
    await summary_check_job()
    
    scheduler.start()
    logging.info("Bot çift katmanlı takip sistemini başlattı (45dk Keşif / 5dk Takip).")
    
    # Render için basit bir sağlık kontrolü (health check) sunucusu
    from aiohttp import web
    async def handle(request):
        return web.Response(text="Bot is running...")
    
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    
    # Botu ve Web Sunucusunu aynı anda çalıştır
    await asyncio.gather(
        dp.start_polling(bot),
        site.start()
    )

if __name__ == "__main__":
    asyncio.run(main())
