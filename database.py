import sqlite3
import datetime

DB_NAME = "matches.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # matches: Maç bilgilerini, başlama saatlerini ve bildirim durumunu tutar
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS matches (
        match_id TEXT PRIMARY KEY,
        teams TEXT,
        start_time DATETIME,
        status TEXT DEFAULT 'PENDING' -- PENDING, NOTIFIED
    )
    ''')
    conn.commit()
    conn.close()

def add_or_update_match(match_id, teams, start_time):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Maç zaten varsa dokunma, yoksa ekle (saatiyle beraber)
    cursor.execute('''
    INSERT OR IGNORE INTO matches (match_id, teams, start_time) 
    VALUES (?, ?, ?)
    ''', (match_id, teams, start_time))
    conn.commit()
    conn.close()

def get_pending_matches():
    """Başlama saatinin üzerinden 120 dakika geçmiş ve henüz bildirilmemiş maçları getirir."""
    now = datetime.datetime.now()
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # TRT (UTC+3) farkını ve 120 dakikayı gözeterek filtrele
    cursor.execute('''
    SELECT match_id, teams, start_time FROM matches 
    WHERE status = 'PENDING'
    ''')
    rows = cursor.fetchall()
    conn.close()
    
    ready_matches = []
    for mid, teams, start_str in rows:
        st = datetime.datetime.fromisoformat(start_str)
        # Eğer (Start + 120 dk) <= Şuan ise maç özeti için uygundur
        if st + datetime.timedelta(minutes=120) <= now:
            ready_matches.append(mid)
            
    return ready_matches

def mark_as_notified(match_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('UPDATE matches SET status = "NOTIFIED" WHERE match_id = ?', (match_id,))
    conn.commit()
    conn.close()
