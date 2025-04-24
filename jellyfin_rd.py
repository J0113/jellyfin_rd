from structure_generator import StructureGenerator
from jellyseerr import Jellyseerr
from torrentio import Torrentio
from cheroot import wsgi
import requests
from settings import Settings
import json

class JellyfinRD:
    def __init__(self, 
                 rd_key: str,
                 jellyseerr_api_key: str,
                 jellyseerr_endpoint = "http://localhost:5055",
                 jellyfin_api_key = "",
                 jellyfin_endpoint = "http://localhost:5055",
                 public_host = "localhost", 
                 host = "0.0.0.0", 
                 port = 8080
                 ):
        """Initialize the proxy server."""
        self.jellyseerr = Jellyseerr(jellyseerr_api_key, jellyseerr_endpoint, jellyfin_api_key, jellyfin_endpoint)
        self.jellyseerr_structure = StructureGenerator("./library", f"http://{public_host}:{port}")
        self.jellyseerr_structure.sync(self.get_paths_jellyseerr())
        self.host = host
        self.port = port
        self.public_host = public_host
        self.server = wsgi.Server((host, port), self.app)
        self.jit_solver = Torrentio(rd_key)
        self.run()



    def app(self, environ, start_response):
        """WSGI Application to handle incoming requests."""
        path = environ.get('PATH_INFO', '').lstrip('/')
        
        if not path:
            start_response('400 Bad Request', [('Content-Type', 'text/plain')])
            return [b'Missing parameters in request URL']
        
        split = path.split("/")
        
        if len(split) == 2 and split[0] == "movie":
            return self.handle_movie(split[1], environ, start_response)

        if len(split) == 4 and split[0] == "show":
            return self.handle_show(split[1], int(split[2]), int(split[3]), environ, start_response)
        
        if split[0] == "jellyseerr":
            return self.handle_jellyseerr(environ, start_response)

        start_response('400 Bad Request', [('Content-Type', 'text/plain')])
        return [b'Missing parameters in request URL']

    def handle_jellyseerr(self, environ, start_response):
        self.jellyseerr_structure.sync(self.get_paths_jellyseerr())
        self.jellyseerr.update_jellyfin()
        start_response('200 OK', [('Content-Type', 'text/plain')])

        # TODO, refresh only by media ID
        # raw_body = environ['wsgi.input'].read(int(environ.get('CONTENT_LENGTH', 0)))
        # body_text = raw_body.decode('utf-8')
        # data = json.loads(body_text)

        # try:
        #     tmdb_id = data['media']['tmdbId']
        #     type = data['media']['media_type']
        #     self.update_jellyfin(tmdb_id, type)
        # except:
        #     pass # Update anyway

        return [b'Started scan']


    def handle_show(self, imdb_id: str, season: int, episode: int, environ, start_response):
        if not self.jit_solver:
            start_response('400 Bad Request', [('Content-Type', 'text/plain')])
            return [b'JIT solver not configured']
        return self.stream_media(self.jit_solver.get_link_show(imdb_id, season, episode), environ, start_response)


    def handle_movie(self, imdb_id: str, environ, start_response):
        if not self.jit_solver:
            start_response('400 Bad Request', [('Content-Type', 'text/plain')])
            return [b'JIT solver not configured']
        return self.stream_media(self.jit_solver.get_link_movie(imdb_id), environ, start_response)


    def update_jellyfin(self, tmdb_id: str, type: str):
        if type in ["movie", "tv"]:
            print(f"Requested: {tmdb_id} of type: {type}")

    def stream_media(self, url, environ, start_response):
        response_headers = [('Location', url)]
        start_response('302 Found', response_headers)
        return [b'Redirecting to stream url: ' + url.encode('utf-8')]

        # The proxy might not be needed:
        headers = {}
        if environ.get('HTTP_RANGE'):
            headers['Range'] = environ['HTTP_RANGE']  # Handle Range requests

        try:
            proxied_response = requests.get(url, headers=headers, stream=True)
            status_code = proxied_response.status_code if proxied_response.status_code != 200 else 206

            response_headers = [
                ('Content-Type', proxied_response.headers.get('Content-Type', 'application/octet-stream')),
                ('Accept-Ranges', 'bytes'),
            ]

            if 'Content-Range' in proxied_response.headers:
                response_headers.append(('Content-Range', proxied_response.headers['Content-Range']))
            
            if 'Content-Length' in proxied_response.headers:
                response_headers.append(('Content-Length', proxied_response.headers['Content-Length']))

            start_response(f'{status_code} OK', response_headers)
            
            return proxied_response.iter_content(chunk_size=8192)
        
        except requests.RequestException as e:
            start_response('500 Internal Server Error', [('Content-Type', 'text/plain')])
            return [f'Error fetching URL: {e}'.encode()] 
    

    def run(self):
        """Start the server."""
        try:
            print(f"Streaming proxy started on http://{self.public_host}:{self.port}.")
            self.server.start()
        except KeyboardInterrupt:
            self.server.stop()
            print("\nServer stopped gracefully.")


    def get_paths_jellyseerr(self):
        (shows, movies) = self.jellyseerr.list_requested()
        paths = []
        for show in shows:
            for season in show.seasons:
                for e in range(1, season.episodes + 1):
                    paths.append(StructureGenerator.Item(f"Shows/{show.name} ({show.year}) [tmdbid-{show.tmdb_id}]/Season {season.season:02d}/{show.name} S{season.season:02d}E{e:02d}", f"show/{show.imdb_id}/{season.season}/{e}"))
        for movie in movies:
            paths.append(StructureGenerator.Item(f"Movies/{movie.name} ({movie.year}) [tmdbid-{movie.tmdb_id}]/{movie.name}", f"movie/{movie.imdb_id}"))
        return paths


s = Settings()

jellyfin_rd = JellyfinRD(
    rd_key = s["real_debrid"]["api_key"],
    jellyseerr_api_key = s["jellyseerr"]["api_key"],
    jellyseerr_endpoint = s["jellyseerr"]["endpoint"],
    jellyfin_api_key = s["jellyfin"]["api_key"],
    jellyfin_endpoint = s["jellyfin"]["endpoint"],
    public_host = s["jellyfin_rd"]["public_host"],
    host = s["jellyfin_rd"]["network_interface"],
    port = s["jellyfin_rd"]["port"]
)