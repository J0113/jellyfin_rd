from __future__ import annotations
import hashlib
import os
import time
import logging
from guessit import guessit
import requests
import itertools
import sqlite3
from datetime import datetime

logging.basicConfig(level=logging.INFO)

class RealDebrid:
    def __init__(self, api_token, database_path = "./config/config.db"):
        self.active_urls = {}
        self.rd = RD(api_token)
        self.db = sqlite3.connect(database_path, check_same_thread=False)
        self.init_db()

    def init_db(self):
        self.sql("CREATE TABLE IF NOT EXISTS [torrents] ([id] TEXT, [name] TEXT, [date] TEXT, [status] TEXT, [bytes] INT, [hash] TEXT);")
        self.sql("CREATE TABLE IF NOT EXISTS [files] ([name] TEXT, [torrent_id] TEXT, [bytes] INT, [link] TEXT, [path] TEXT, [tag] TEXT, [original_path] TEXT);")

    def sql(self, query, parameters = ()):
        try:
            c = self.db.cursor()
            c.execute(query, parameters)
            self.db.commit()
            return c.fetchall()
        except Exception as e:
            print(e)
            return False

    def get_torrents(self, torrent_id = "") -> list[Torrent]:
        torrents_array = []

        if torrent_id != "":
            torrents = self.sql("SELECT id, name, date, status, bytes, hash FROM torrents WHERE id = ?", (torrent_id,))
        else: 
            torrents = self.sql("SELECT id, name, date, status, bytes, hash FROM torrents WHERE status = 'downloaded'")

        for torrent in torrents:
            creation_date = datetime.strptime(torrent[2], "%Y-%m-%dT%H:%M:%S.%fZ").timestamp()
            files = self.sql("SELECT name, torrent_id, bytes, link, path, tag, original_path FROM files WHERE torrent_id = ?", (torrent[0],))
            files_array = []
            for file in files:
                files_array.append(File(self, file[0], file[2], file[3], file[4], creation_date, file[5], file[6]))
            torrents_array.append(Torrent(torrent[0], torrent[1], torrent[2], torrent[3], torrent[4], torrent[5], files_array))
        return torrents_array

    def get_torrent(self, id) -> Torrent:
        torrents = self.get_torrents(torrent_id = id)
        return torrents[0] if len(torrents) > 0 else None
    
    def get_file(self, tag: str) -> File:
        file = self.sql("SELECT name, torrent_id, bytes, link, path, tag, original_path FROM files WHERE tag = ?", (tag,))
        if len(file) == 0:
            return None
        return File(self, file[0][0], file[0][2], file[0][3], file[0][4], datetime.now().timestamp(), file[0][5], file[0][6])

    def update_torrent(self, torrent_id) -> Torrent:
        info = self.rd.torrents.info(torrent_id).json()
        self.remove_torrent(torrent_id)
        self.sql("INSERT INTO torrents (id, name, date, status, bytes, hash) VALUES (?,?,?,?,?,?)", (info["id"], info["filename"], info["added"], info["status"], info["bytes"], info["hash"]))
        
        file_iterator = 0
        for file in info["files"]:
            if file["selected"]:
                filename = os.path.basename(file["path"])
                tag = hashlib.md5((filename + str(file["bytes"])).encode('utf-8')).hexdigest()
                formated_path = self.parse_file(filename)
                self.sql("INSERT INTO files (name, torrent_id, bytes, link, path, tag, original_path) VALUES (?,?,?,?,?,?, ?);", (filename, info["id"], file["bytes"], info["links"][file_iterator], formated_path, tag, file["path"]))
                file_iterator = file_iterator + 1

        return self.get_torrent(torrent_id)

    def remove_torrent(self, torrent_id):
        self.sql("DELETE FROM torrents WHERE id = ?", (torrent_id,))
        self.sql("DELETE FROM files WHERE torrent_id = ?;", (torrent_id,))

    def update_torrents(self, limit=1000, page=1, force=False) -> list[Torrent]:
        torrent_ids = [torrent.id for torrent in self.get_torrents()]

        torrents = self.rd.torrents.get(limit=limit, page=page).json()
        for torrent in torrents:
            if torrent["id"] in torrent_ids:
                torrent_ids.remove(torrent["id"])
            if force == False:
                existing_torrent = self.get_torrent(torrent["id"])
                if existing_torrent != None and existing_torrent.status == torrent["status"]:
                    print("Using cached torrent: " + existing_torrent.name)
                    continue
            print("Updating info for: " + torrent["filename"])
            self.update_torrent(torrent["id"])
        
        for torrent_id in torrent_ids:
            self.remove_torrent(torrent_id)
            print(f"Removing {torrent_id}")

        return self.get_torrents()

    def get_file_url(self, file: File) -> str:
        if file.tag in self.active_urls:
            return self.active_urls[file.tag]
        link = self.rd.unrestrict.link(link=file.link).json()["download"]
        self.active_urls[file.tag] = link
        return link

    def update_file_urls(self):
        urls = self.rd.downloads.get(page=1, limit=5000 ).json()
        for url in urls:
            tag = hashlib.md5((url["filename"] + str(url["filesize"])).encode('utf-8')).hexdigest()
            if tag not in self.active_urls:
                self.active_urls[tag] = url["download"]

    def parse_file(self, path) -> str:
        shows_folder = "Shows"
        movies_folder = "Movies"
        try:
            result = guessit(path)
            screensize = f" - [{result["screen_size"]}]" if "screen_size" in result else ""
            if result["type"] == "episode":
                strm_file = f"{shows_folder}/{result["title"]}/Season {result["season"]:02d}/{result["title"]} S{result["season"]:02d}E{result["episode"]:02d}"
            elif result["type"] == "movie":
                year = " (" + str(result["year"]) + ")" if "year" in result else ""
                strm_file = f"{movies_folder}/{result["title"]}{year}/{result["title"]}{year}{screensize}"
            return strm_file
        except Exception as e:
            print(f"'{path}' cannot be parsed as valid media: {e}")
            return ""

class File:
    def __init__(self, rd: RealDebrid, name: str, bytes: int, link: str, path: str, creation_date: float, tag: str, original_path: str):
        self.rd = rd
        self.name = name
        self.bytes = bytes
        self.link = link
        self.path = path
        self.creation_date = creation_date
        self.tag = tag
        self.original_path = original_path

    def get_download_link(self) -> str:
        return self.rd.get_file_url(self)

class Torrent:
    def __init__(self, id: str, name: str, date: str, status: str, filesize: int, filehash: str, files = list[File]):
        self.id = id
        self.name = name
        self.date = date
        self.status = status
        self.bytes = filesize
        self.hash = filehash
        self.files = files

    def getFiles(self) -> list[File]:
        return self.files


# API by s-krilla (rd_api_py)
# Modified to work better with jellyfin_rd.
# https://github.com/s-krilla/rd_api_py
class RD:
    def __init__(self, api_token):
        self.rd_apitoken = api_token
        self.base_url = 'https://api.real-debrid.com/rest/1.0'
        self.header = {'Authorization': "Bearer " + str(self.rd_apitoken)}   
        self.error_codes = self.get_error_codes()
        self.sleep = 0.5
        self.long_sleep = 30
        self.count_obj = itertools.cycle(range(0, 501))
        self.count = next(self.count_obj)

        # Check the API token
        self.check_token()

        self.system = self.System(self)
        self.user = self.User(self)
        self.unrestrict = self.Unrestrict(self)
        self.traffic = self.Traffic(self)
        self.streaming = self.Streaming(self)
        self.downloads = self.Downloads(self)
        self.torrents = self.Torrents(self)
        self.hosts = self.Hosts(self)
        self.settings = self.Settings(self)

    def get(self, path, **options):
        request = requests.get(self.base_url + path, headers=self.header, params=options)
        return self.handler(request, self.error_codes, path)

    def post(self, path, **payload):
        request = requests.post(self.base_url + path, headers=self.header, data=payload)
        return self.handler(request, self.error_codes, path)
    
    def put(self, path, filepath, **payload):
        with open(filepath, 'rb') as file:
            request = requests.put(self.base_url + path, headers=self.header, data=file, params=payload)
        return self.handler(request, self.error_codes, path)

    def delete(self, path):
        request = requests.delete(self.base_url + path, headers=self.header)
        return self.handler(request, self.error_codes, path)
    
    def handler(self, request, error_codes, path):
        try:
            request.raise_for_status()
        except requests.exceptions.HTTPError as errh:
            logging.error('%s at %s', errh, path)
        except requests.exceptions.ConnectionError as errc:
            logging.error('%s at %s', errc, path)
        except requests.exceptions.Timeout as errt:
            logging.error('%s at %s', errt, path)
        except requests.exceptions.RequestException as err:
            logging.error('%s at %s', err, path)
        try:
            if 'error_code' in request.json():
                code = request.json()['error_code']
                message = error_codes.get(str(code), 'Unknown error')
                logging.warning('%s: %s at %s', code, message, path)
        except:
            pass
        self.handle_sleep()
        return request  
    
    def check_token(self):
        if self.rd_apitoken is None or self.rd_apitoken == 'your_token_here':
            logging.warning('Add token to .env')

    def handle_sleep(self):
        if self.count < 500:
            logging.debug('Sleeping %ss', self.sleep)
            time.sleep(self.sleep)
        elif self.count == 500:
            logging.debug('Sleeping %ss', self.long_sleep)
            time.sleep(self.long_sleep)
            self.count = 0

    def get_error_codes(self):
        return {
            "-1": "Internal error",
            "1": "Missing parameter",
            "2": "Bad parameter value",
            "3": "Unknown method",
            "4": "Method not allowed",
            "5": "Slow down",
            "6": "Ressource unreachable",
            "7": "Resource not found",
            "8": "Bad token",
            "9": "Permission denied",
            "10": "Two-Factor authentication needed",
            "11": "Two-Factor authentication pending",
            "12": "Invalid login",
            "13": "Invalid password",
            "14": "Account locked",
            "15": "Account not activated",
            "16": "Unsupported hoster",
            "17": "Hoster in maintenance",
            "18": "Hoster limit reached",
            "19": "Hoster temporarily unavailable",
            "20": "Hoster not available for free users",
            "21": "Too many active downloads",
            "22": "IP Address not allowed",
            "23": "Traffic exhausted",
            "24": "File unavailable",
            "25": "Service unavailable",
            "26": "Upload too big",
            "27": "Upload error",
            "28": "File not allowed",
            "29": "Torrent too big",
            "30": "Torrent file invalid",
            "31": "Action already done",
            "32": "Image resolution error",
            "33": "Torrent already active",
            "34": "Too many requests",
            "35": "Infringing file",
            "36": "Fair Usage Limit"
        }


    class System:
        def __init__(self, rd_instance):
            self.rd = rd_instance

        def disable_token(self):
            return self.rd.get('/disable_access_token')

        def time(self):
            return self.rd.get('/time')

        def iso_time(self):
            return self.rd.get('/time/iso')

    class User:
        def __init__(self, rd_instance):
            self.rd = rd_instance

        def get(self):
            return self.rd.get('/user')

    class Unrestrict:
        def __init__(self, rd_instance):
            self.rd = rd_instance

        def check(self, link, password=None):
            return self.rd.post('/unrestrict/check', link=link, password=password)

        def link(self, link, password=None, remote=None):
            return self.rd.post('/unrestrict/link', link=link, password=password, remote=remote)
        
        def folder(self, link):
            return self.rd.post('/unrestrict/folder', link=link)
        
        def container_file(self, filepath):
            return self.rd.put('/unrestrict/containerFile', filepath=filepath)

        def container_link(self, link):
            return self.rd.post('/unrestrict/containerLink', link=link)
        
    class Traffic:
        def __init__(self, rd_instance):
            self.rd = rd_instance

        def get(self):
            return self.rd.get('/traffic')

        def details(self, start=None, end=None):
            return self.rd.get('/traffic/details', start=start, end=end)        
        
    class Streaming:
        def __init__(self, rd_instance):
            self.rd = rd_instance

        def transcode(self, id):
            return self.rd.get('/streaming/transcode/' + str(id))

        def media_info(self, id):
            return self.rd.get('/streaming/mediaInfos/' + str(id))
        
    class Downloads:
        def __init__(self, rd_instance):
            self.rd = rd_instance

        def get(self, offset=None, page=None, limit=None ):
            return self.rd.get('/downloads', offset=offset, page=page, limit=limit)
        
        def delete(self, id):
            return self.rd.delete('/downloads/delete/'+ str(id))

    class Torrents:
        def __init__(self, rd_instance):
            self.rd = rd_instance

        def get(self, offset=None, page=None, limit=None, filter=None ):
            return self.rd.get('/torrents', offset=offset, page=page, limit=limit, filter=filter)
        
        def info(self, id):
            return self.rd.get('/torrents/info/' + str(id))

        def instant_availability(self, hash):
            return self.rd.get('/torrents/instantAvailability/' + str(hash))

        def active_count(self):
            return self.rd.get('/torrents/activeCount')
        
        def available_hosts(self):
            return self.rd.get('/torrents/availableHosts')

        def add_file(self, filepath, host=None):
            return self.rd.put('/torrents/addTorrent', filepath=filepath, host=host)
        
        def add_magnet(self, magnet, host=None):
            magnet_link = 'magnet:?xt=urn:btih:' + str(magnet)
            return self.rd.post('/torrents/addMagnet', magnet=magnet_link, host=host)
        
        def select_files(self, id, files):
            return self.rd.post('/torrents/selectFiles/' + str(id), files=str(files))
        
        def delete(self, id):
            return self.rd.delete('/torrents/delete/' + str(id))

    class Hosts:
        def __init__(self, rd_instance):
            self.rd = rd_instance

        def get(self):
            return self.rd.get('/hosts')        
        
        def status(self):
            return self.rd.get('/hosts/status')   

        def regex(self):
            return self.rd.get('/hosts/regex')  

        def regex_folder(self):
            return self.rd.get('/hosts/regexFolder')  

        def domains(self):
            return self.rd.get('/hosts/domains')  

    class Settings:
        def __init__(self, rd_instance):
            self.rd = rd_instance

        def get(self):
            return self.rd.get('/settings')
        
        def update(self, setting_name, setting_value):
            return self.rd.post('/settings/update', setting_name=setting_name, setting_value=setting_value)
        
        def convert_points(self):
            return self.rd.post('/settings/convertPoints')            

        def change_password(self):
            return self.rd.post('/settings/changePassword')      

        def avatar_file(self, filepath):
            return self.rd.put('/settings/avatarFile', filepath=filepath)
        
        def avatar_delete(self):
            return self.rd.delete('/settings/avatarDelete')
