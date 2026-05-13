FROM python:3.11-slim

WORKDIR /srv

# Dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates \
    docker.io \
    libpq-dev gcc \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /srv/requirements.txt
RUN pip install --no-cache-dir -r /srv/requirements.txt

COPY app /srv/app

ENV PYTHONUNBUFFERED=1

EXPOSE 8000
