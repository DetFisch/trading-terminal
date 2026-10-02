ARG BUILD_FROM=python:3.12-slim-bookworm
FROM ${BUILD_FROM}

ENV PIP_NO_CACHE_DIR=1 PYTHONUNBUFFERED=1 DATA_DIR=/data
WORKDIR /app

# Dependencies first so code-only updates rebuild quickly
COPY app/requirements.txt .
RUN pip install -r requirements.txt

COPY app/ .
COPY addon_entry.py .

CMD ["python", "addon_entry.py"]
