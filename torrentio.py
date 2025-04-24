from curl_cffi import requests

class Torrentio:

    def __init__(self, rd_api_key: str, endpoint = "https://torrentio.strem.fun"):
        self.api_key = rd_api_key
        self.endpoint = endpoint
        self.cached_urls = {}

    def get_streams_show(self, imdb_id: str, season: int, episode: int):
        request = requests.get(f"{self.endpoint}/sizefilter=10GB|sort=qualitysize|qualityfilter=scr,cam|limit=10|debridoptions=nodownloadlinks,nocatalog|realdebrid={self.api_key}/stream/series/{imdb_id}%3A{season}%3A{episode}.json").json()
        return [self.Result(stream['name'], stream['title'], stream['url']) for stream in request['streams'] if "streams" in request and len(request['streams']) > 0]

    def get_streams_movie(self, imdb_id: str):
        url = f"{self.endpoint}/sizefilter=10GB|sort=qualitysize|qualityfilter=scr,cam|limit=10|debridoptions=nodownloadlinks,nocatalog|realdebrid={self.api_key}/stream/movie/{imdb_id}.json"
        request = requests.get(url).json()
        return [self.Result(stream['name'], stream['title'], stream['url']) for stream in request['streams'] if "streams" in request and len(request['streams']) > 0]
    
    def resolve_url(self, url):
        request = requests.head(url, allow_redirects=True)
        return request.url
    
    def get_link_show(self, imdb_id: str, season: int, episode: int):
        key = f"{imdb_id}|{season}|{episode}"
        if key not in self.cached_urls.keys():
            streams = self.get_streams_show(imdb_id, season, episode)
            self.cached_urls[key] = self.resolve_url(streams[0].url)
        return self.cached_urls[key]

    def get_link_movie(self, imdb_id: str):
        if imdb_id not in self.cached_urls.keys():
            streams = self.get_streams_movie(imdb_id)
            self.cached_urls[imdb_id] = self.resolve_url(streams[0].url)
        return self.cached_urls[imdb_id]

    class Result:
        def __init__(self, name, title, url):
            self.name = name
            self.title = title
            self.url = url
    