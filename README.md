# jellyfin_rd 
jellyfin_rd can take a real debrid libary and convert it to structured .strm files that Jellyfin can read. 

## Example output
```
.
├── Movies
│   └── Big Buck Bunny (2008)
│       └── Big Buck Bunny (2008) - [1080p].strm
└── Shows
```

## Getting started
Easiest way to get started is with docker compose.
```yaml
services:
  jellyfin_rd:
    container_name: jellyfin_rd
    image: j0113/jellyfin_rd:latest
    volumes:
      - ./libary:/jellyfin-rd/library                # Mount the libary folder on the docker host.
      - ./settings.json:/jellyfin-rd/settings.json   # Mount the settings file
    ports:
      - "8080:8080"
```