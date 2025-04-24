from __future__ import annotations
import requests

class Jellyseerr:

    def __init__(self, api_key: str, host = "http://localhost:5055", jellyfin_api_key = "", jellyfin_host = "http://localhost:8096"):
        self.api_key = api_key
        self.endpoint = host + "/api/v1/"
        self.jellyfin_api_key = jellyfin_api_key
        self.jellyfin_host = jellyfin_host

    def list_requested(self) -> tuple[list[Jellyseerr.Show],list[Jellyseerr.Movie]]:
        shows = []
        movies = []

        requests = self.get("request", {
            'take': 1000,
            'skip': 0,
            'filter': 'all', # approved
            'sort': 'added'
        })['results']

        for request in requests:
            tmdbId = request['media']['tmdbId']
            if request['type'] == "tv":
                shows.append(self.parse_show(tmdbId))
            elif request['type'] == "movie":
                movies.append(self.parse_movie(tmdbId))
        
        return (shows, movies)

    def parse_movie(self, tmdb_id: int):
        movie = self.get("movie/" + str(tmdb_id))
        return self.Movie(movie['title'], int(movie['releaseDate'][:4]), movie['externalIds']['imdbId'], tmdb_id)

    def parse_show(self, tmdb_id: int):
        show = self.get("tv/" + str(tmdb_id))
        seasons = [self.Season(s['seasonNumber'], s['episodeCount']) for s in show['seasons'] if s['seasonNumber'] > 0]
        return self.Show(show['originalName'], show['firstAirDate'][:4], show['externalIds']['imdbId'], tmdb_id, seasons)



    def update_jellyfin(self):
        if self.jellyfin_api_key != "":
            headers = {
                'accept': 'application/json',
                'Authorization': f"MediaBrowser Token=\"{self.jellyfin_api_key}\", Client=\"Jellyfin_RD Refresh\""
            }
            request = requests.post(self.jellyfin_host + "/Library/Refresh", headers=headers)

            if request.status_code > 399:
                raise Exception(request.text) 


    def list_requests(self):
        return self.get("request", {
            'take': 1000,
            'skip': 0,
            'filter': 'all',
            'sort': 'added'
        })
    
    def current_user(self):
        return self.get("auth/me")
    
    def get(self, path: str, params = {}):
        headers = {
            'accept': 'application/json',
            'X-Api-Key': self.api_key
        }
        request = requests.get(self.endpoint + path, headers=headers, params=params)

        if request.status_code > 399:
            raise Exception(request.text) 

        return request.json()
    


    class Movie:
        def __init__(self, name: str, year: int, imdb_id: str, tmdb_id: int):
            self.name = name
            self.year = year
            self.imdb_id = imdb_id
            self.tmdb_id = tmdb_id

    class Show:
        def __init__(self, name: str, year: int, imdb_id: str, tmdb_id: int, seasons: list[Jellyseerr.Season]):
            self.name = name
            self.year = year
            self.imdb_id = imdb_id
            self.tmdb_id = tmdb_id
            self.seasons = seasons
    
    class Season:
        def __init__(self, season: int, episodes: int):
            self.season = season
            self.episodes = episodes
