FROM python:3.11-slim

ARG WB_RND_BUILD_COMMIT

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN printf '%s' "$WB_RND_BUILD_COMMIT" > /app/.wellnessbox-rnd-image-commit \
    && chmod 0444 /app/.wellnessbox-rnd-image-commit

COPY pyproject.toml README.md ./
COPY src ./src
COPY apps ./apps
COPY data ./data
COPY scripts ./scripts

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

EXPOSE 8000

CMD ["python", "scripts/start_inference_api.py"]
