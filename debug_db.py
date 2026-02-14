import sqlite3
from database import DB_NAME

def check_db():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT team_a, team_b, start_time, end_time FROM tracked_matches")
        rows = cursor.fetchall()
        if not rows:
            print("Veritabanında henüz takip edilen maç yok.")
        else:
            print("--- Takip Edilen Maçlar ---")
            for row in rows:
                print(f"Maç: {row[0].upper()} vs {row[1].upper()}")
                print(f"Başlangıç: {row[2]}")
                print(f"Takip Başlangıcı (Maç + 120dk): {row[3]}")
                print("-" * 20)
        conn.close()
    except Exception as e:
        print(f"Hata: {e}")

if __name__ == "__main__":
    check_db()
