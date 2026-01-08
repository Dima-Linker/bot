import time
from db.database import init_db
from db.repo import Repo

# Global scan lock to prevent overlapping scans
SCAN_RUNNING = False

def scheduler_loop(scan_fn, interval_seconds: int = 300, cleanup_interval: int = 3600):  # Cleanup every hour
    global SCAN_RUNNING
    last_cleanup = time.time()
    
    while True:
        start = time.time()
        
        # Scan lock - skip if previous scan still running
        if SCAN_RUNNING:
            print("[SCHED] SKIP: previous scan still running")
        else:
            SCAN_RUNNING = True
            try:
                scan_fn()
            except Exception as e:
                print(f'[SCHED] scan_fn error: {e}')
            finally:
                SCAN_RUNNING = False

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
                
        duration = time.time() - start
        time.sleep(max(1, interval_seconds - int(duration)))