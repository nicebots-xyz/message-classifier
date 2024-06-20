FROM python:3.11-slim-bookworm

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# we move to the app folder and run the pip install command
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y \
    curl \
    build-essential

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app.py /app/app.py
COPY ./src /app/
RUN mkdir /app/cache
RUN adduser -u 9263 --disabled-password --gecos "" appuser && chown -R appuser /app

USER appuser
HEALTHCHECK CMD curl --fail http://localhost:8000/v1/health || exit 1

CMD ["fastapi", "run"]