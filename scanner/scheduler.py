import time
from db.database import init_db
from db.repo import Repo


def scheduler_loop(scan_fn, interval_seconds: int = 300, cleanup_interval: int = 3600):  # Cleanup every hour
    last_cleanup = time.time()
    
    while True:
        start = time.time()
        try:
            scan_fn()
            
            # Periodic cleanup of expired setups
            now = time.time()
            if now - last_cleanup >= cleanup_interval:
                try:
                    conn = init_db('./data/bot.db', './db/schema.sql')
                    repo = Repo(conn)
                    cleaned_count = repo.cleanup_expired_setups()
                    if cleaned_count > 0:
                        print(f'🧹 Auto-cleanup: {cleaned_count} abgelaufene Setups entfernt')
                    conn.close()
                    last_cleanup = now
                except Exception as cleanup_e:
                    print(f'Cleanup error: {cleanup_e}')
                    
        except Exception as e:
            print('Scan error:', e)
        duration = time.time() - start
        time.sleep(max(1, interval_seconds - int(duration)))