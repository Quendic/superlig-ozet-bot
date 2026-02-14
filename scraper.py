import httpx
from bs4 import BeautifulSoup
import logging
import datetime
import re

SUMMARY_URL = "https://beinsports.com.tr/mac-ozetleri-goller/super-lig"

async def scrape_all_matches():
    """
    Sayfadaki tüm bugünkü maçları, saatlerini ve (varsa) özet linklerini toplar.
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
            today_d_m = f"{now.day} {['Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık'][now.month-1]}"

            # Özet sayfası Linklerini ve Maç Bloklarını bulalım
            # beIN sayfasında her maç bir blok içindedir.
            all_links = soup.find_all('a', href=lambda h: h and ('/mac-merkezi/' in h or '/ozet/' in h))
            
            for link in all_links:
                href = link.get('href', '')
                parent = link.find_parent(['div', 'section', 'li'], class_=lambda c: c and ('match' in c or 'card' in c or 'item' in c)) or link.parent
                
                text = parent.get_text().strip()
                
                # Tarih kontrolü (Sadece bugünün maçları)
                if not (today_d_m.upper() in text.upper() or "BUGÜN" in text.upper() or now.strftime("%d.%m.%Y") in text):
                    continue
                
                # Maç ID ve Takımlar
                url_parts = href.split('/')
                match_id = url_parts[-1].split('?')[0]
                if not match_id or len(match_id) < 5: continue
                
                # Başlama saati bul (HH:MM)
                time_match = re.search(r'([012][0-9]:[0-5][0-9])', text)
                start_time = now # Varsayılan
                if time_match:
                    h, m = map(int, time_match.group(1).split(':'))
                    # beIN UTC veriyorsa +3 ekle, eğer zaten TRT ise düz kullan 
                    # (Özet sayfasındakiler genelde TRT görünür)
                    start_time = now.replace(hour=h, minute=m, second=0, microsecond=0)

                # Eğer bu link bir özet linkiyse URL'yi kaydet
                summary_url = None
                if "OZETI IZLE" in text.upper() or "/ozet/" in href:
                    summary_url = href if href.startswith("http") else "https://beinsports.com.tr" + href

                if match_id not in results:
                    results[match_id] = {
                        'teams': match_id.replace("-mac-ozeti", "").replace("-", " ").title(),
                        'start_time': start_time,
                        'url': summary_url
                    }
                elif summary_url: # Daha önce saati bulduysak şimdi linki ekleyelim
                    results[match_id]['url'] = summary_url

            return list(results.values())

    except Exception as e:
        logging.error(f"Scraper hatası: {e}")
        return []
