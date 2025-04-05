from real_debrid import RealDebrid
import os

class StructureGenerator:
    def __init__(self, rd: RealDebrid, path: str, base_url: str):
        self.rd = rd
        self.path = os.path.abspath(path)
        self.base_url = base_url
        self.paths = []

    def sync(self):
        print(f"Starting sync to {self.path}")
        torrents = self.rd.get_torrents()
        self.paths = []
        for torrent in torrents:
            for file in torrent.getFiles():
                if file.path == "":
                    continue
                strm_file = os.path.join(self.path, f"{file.path}.strm")
                self.paths.append(strm_file)
                self.create_file_if_needed(strm_file, f"{self.base_url}/{file.tag}")
        self.remove_old_files()

    def create_file_if_needed(self, file: str, text: str):
        directory = os.path.dirname(file)
        if directory and not os.path.exists(directory):
            try:
                os.makedirs(directory)
            except OSError as e:
                print(f"Error creating directory {directory}: {e}")
                return
        try:
            with open(file, 'w') as f:
                f.write(text)
        except IOError as e:
            print(f"Error writing to {file}: {e}")
    
    def remove_old_files(self):
        for root, dirs, files in os.walk(self.path, topdown=False):
            # Remove files that aren't in our sync list
            for file in files:
                file_path = os.path.join(root, file)
                if file_path not in self.paths and file_path.endswith('.strm'):
                    try:
                        os.remove(file_path)
                    except OSError as e:
                        print(f"Error cleaning up {file_path}: {e}")
            
            # Remove empty directories
            if not os.listdir(root):
                try:
                    os.rmdir(root)
                except OSError as e:
                    print(f"Error cleaning up {root}: {e}")