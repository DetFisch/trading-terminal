# Base image fixed here on purpose: Home Assistant passes its own Alpine base as BUILD_FROM
# (no Python), so that argument is deliberately not used.
FROM python:3.12-slim-bookworm

ENV PIP_NO_CACHE_DIR=1 PYTHONUNBUFFERED=1 DATA_DIR=/data
WORKDIR /app

# Dependencies first so code-only updates rebuild quickly
COPY app/requirements.txt .
RUN pip install -r requirements.txt

COPY app/ .
COPY addon_entry.py .

CMD ["python", "addon_entry.py"]
