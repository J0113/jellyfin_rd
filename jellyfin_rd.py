import os
from stream_proxy import StreamProxy
from real_debrid import RealDebrid
from structure_generator import StructureGenerator
import threading
from time import sleep
import sys

class JellyfinRD:

    def __init__(self, rd_key: str, library_path = "./library", public_host = "localhost", database_path = "./config/config.db" , host = "0.0.0.0", port = 8080):
        self.rd = RealDebrid(rd_key, database_path)
        self.structure = StructureGenerator(self.rd, library_path, f"http://{public_host}:{port}")
        threading.Thread(target=self.scheduler, daemon=True).start()
        proxy = StreamProxy(self.rd, host, port)
        proxy.run()

    def scheduler(self):
        print(f"Starting scheduler..")
        while True:
            self.rd.update_file_urls()
            self.rd.update_torrents()
            self.structure.sync()
            print("Scheduled tasks finished, sleeping for 60s.")
            sleep(60)

if __name__ == "__main__":
    RD_KEY = os.getenv("RD_KEY")
    if RD_KEY:
        LIBRARY_PATH = os.getenv("LIBRARY_PATH", "./library")
        PUBLIC_HOST = os.getenv("PUBLIC_HOST", "localhost")
        DB_PATH = os.getenv("DB_PATH", "./config/config.db")
        HOST = os.getenv("HOST", "0.0.0.0")
        PORT = int(os.getenv("PORT", 8080))
        jellyfin_rd = JellyfinRD(RD_KEY, LIBRARY_PATH, PUBLIC_HOST, DB_PATH, HOST, PORT)
        sys.exit(0)
    else:
        print("Error: RD_KEY is not set.")
        sys.exit(1)