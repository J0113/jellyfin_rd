FROM python:3-alpine
WORKDIR /jellyfin-rd
COPY jellyfin_rd.py .
COPY jellyseerr.py .
COPY settings.py .
COPY structure_generator.py .
COPY torrentio.py .
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
CMD ["python", "-u", "jellyfin_rd.py"]
