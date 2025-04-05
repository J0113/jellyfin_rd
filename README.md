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
    environment:
      - RD_KEY=PASTE YOUR Real Debrid KEY HERE
      # - LIBRARY_PATH=/jellyfin-rd/library
      # - PUBLIC_HOST=localhost
      # - DB_PATH =./config/config.db
      # - HOST=0.0.0.0
      # - PORT=8080
    volumes:
      - ./libary:/jellyfin-rd/library
      - ./config:/jellyfin-rd/config
    ports:
      - "8080:8080"
```