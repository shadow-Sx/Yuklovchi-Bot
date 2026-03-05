import threading
import time
import requests
from config import KEEP_ALIVE_URL


def keep_alive():
    if not KEEP_ALIVE_URL:
        return

    def ping():
        while True:
            try:
                requests.get(KEEP_ALIVE_URL)
            except:
                pass
            time.sleep(60)

    threading.Thread(target=ping, daemon=True).start()
