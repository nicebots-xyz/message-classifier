FROM python:3.11-slim-bookworm
WORKDIR /app

# INSTALLING DEPENDENCIES
RUN apt-get update && apt-get install -y curl build-essential
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1
ADD requirements.txt /app/requirements.txt
RUN export TORCH_VERSION=$(grep torch== requirements.txt | cut -d'=' -f3) && \
    pip install torch==$TORCH_VERSION --index-url https://download.pytorch.org/whl/cpu --no-cache-dir && \
    pip install -r requirements.txt --no-cache-dir

# ADDING FILES
ADD app.py /app/app.py
ADD ./src /app/
RUN mkdir /app/cache

# ADDING USER
RUN adduser -u 9263 --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser

HEALTHCHECK CMD curl --fail http://localhost:8000/v1/health || exit 1
EXPOSE 8000

ENTRYPOINT ["fastapi"]
CMD ["run"]