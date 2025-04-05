from cheroot import wsgi
import requests
from real_debrid import RealDebrid, File

class StreamProxy:
    def __init__(self, rd: RealDebrid, host='0.0.0.0', port=8080):
        """Initialize the proxy server."""
        self.host = host
        self.port = port
        self.rd = rd
        self.server = wsgi.Server((host, port), self.app)

    def file_by_tag(self, tag) -> File:
        return self.rd.get_file(tag)

    def app(self, environ, start_response):
        """WSGI Application to handle incoming requests."""
        path = environ.get('PATH_INFO', '').lstrip('/')
        
        if not path:
            start_response('400 Bad Request', [('Content-Type', 'text/plain')])
            return [b'Missing ID in request URL']

        file = self.file_by_tag(path)
        if not file:
            start_response('404 Not Found', [('Content-Type', 'text/plain')])
            return [b'Invalid ID in request URL']

        headers = {}
        if environ.get('HTTP_RANGE'):
            headers['Range'] = environ['HTTP_RANGE']  # Handle Range requests

        try:
            proxied_response = requests.get(file.get_download_link(), headers=headers, stream=True)
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
            print(f"Streaming proxy started on http://{self.host}:{self.port}.")
            self.server.start()
        except KeyboardInterrupt:
            self.server.stop()
            print("\nServer stopped gracefully.")