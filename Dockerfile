FROM python:3-alpine
WORKDIR /jellyfin-rd
COPY jellyfin_rd.py .
COPY real_debrid.py .
COPY stream_proxy.py .
COPY structure_generator.py .
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
CMD ["python", "-u", "jellyfin_rd.py"]
