import httpx
from bs4 import BeautifulSoup
import logging
import datetime
import re

SUMMARY_URL = "https://beinsports.com.tr/mac-ozetleri-goller/super-lig"

async def scrape_all_matches():
    """
    Sayfadaki tüm bugünkü maçları, saatlerini ve (varsa) özet linklerini toplar.
    Tarih başlıklarını da hesaba katar.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
            response = await client.get(SUMMARY_URL, timeout=15)
            if response.status_code != 200:
                return []

            soup = BeautifulSoup(response.text, 'html.parser')
            results = {} # match_id -> {teams, start_time, url}
            
            now = datetime.datetime.now()
            months = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
            today_d_m = f"{now.day} {months[now.month-1]}"
            today_iso = now.strftime("%d.%m.%Y")

            # Özet sayfası Linklerini bulalım
            all_links = soup.find_all('a', href=lambda h: h and ('/mac-merkezi/' in h or '/ozet/' in h))
            
            for link in all_links:
                href = link.get('href', '')
                # Maçı içeren temel kapsayıcıyı bul (class'ında 'match' veya 'card' olan en yakın div)
                card = link.find_parent(['div', 'section', 'li'], class_=lambda c: c and ('match' in c or 'card' in c or 'item' in c)) or link.parent
                
                # Tarih Kontrolü: Kartın içinde tarih yoksa yukarıdaki başlıklara bak
                is_today = False
                card_text = card.get_text().strip().upper()
                
                if (today_d_m.upper() in card_text or "BUGÜN" in card_text or today_iso in card_text):
                    is_today = True
                else:
                    # Geriye doğru en yakın tarih başlığını ara
                    prev_headers = link.find_all_previous(['h1', 'h2', 'h3', 'h4', 'div', 'span'])
                    for h in prev_headers:
                        h_text = h.get_text().strip().upper()
                        if today_d_m.upper() in h_text or "BUGÜN" in h_text:
                            is_today = True
                            break
                        # Eğer başka bir tarih formatı bulursak (örn dün) ve bugünü bulamadıysak dur
                        if re.search(r'\d{1,2} [A-ZÇĞİÖŞÜ]+', h_text):
                            break
                
                if not is_today:
                    continue
                
                # Maç ID ve Takımlar
                url_parts = href.split('/')
                match_id = url_parts[-1].split('?')[0]
                if not match_id or len(match_id) < 5: continue
                
                # Başlama saatini kart içinden bul (HH:MM)
                time_match = re.search(r'([012][0-9]:[0-5][0-9])', card_text)
                start_time = now.replace(hour=20, minute=0) # Bulamazsak varsayılan 20:00 (TR-FB saati)
                if time_match:
                    h, m = map(int, time_match.group(1).split(':'))
                    start_time = now.replace(hour=h, minute=m, second=0, microsecond=0)

                summary_url = None
                if "OZETI IZLE" in card_text or "/ozet/" in href:
                    summary_url = href if href.startswith("http") else "https://beinsports.com.tr" + href

                if match_id not in results:
                    results[match_id] = {
                        'match_id': match_id,
                        'teams': match_id.replace("-mac-ozeti", "").replace("-", " ").title(),
                        'start_time': start_time,
                        'url': summary_url
                    }
                elif summary_url:
                    results[match_id]['url'] = summary_url

            return list(results.values())

    except Exception as e:
        logging.error(f"Scraper hatası: {e}")
        return []
