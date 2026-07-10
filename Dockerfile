# Portable local agent. Runs the unmoderated tradecraft agent against a local Ollama.
# By default it talks to the HOST's Ollama (reusing your pulled abliterated models);
# override OLLAMA_BASE to point elsewhere.
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY tradecraft/ ./tradecraft/
COPY agent/ ./agent/
COPY detectors/ ./detectors/

ENV OLLAMA_BASE=http://host.docker.internal:11434
ENV TRADECRAFT_LOCAL_MODEL=huihui_ai/qwen2.5-abliterate:14b

# Usage:  docker run --rm --add-host host.docker.internal:host-gateway <img> "your task"
ENTRYPOINT ["python", "-m", "agent"]
