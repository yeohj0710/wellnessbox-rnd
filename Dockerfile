FROM python:3.11-slim

ARG WB_RND_BUILD_COMMIT

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY apps ./apps
COPY data ./data
COPY scripts ./scripts

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

RUN IMAGE_COMMIT_PATH="$(python -c 'from wellnessbox_rnd.deployment import IMAGE_COMMIT_PATH; print(IMAGE_COMMIT_PATH)')" \
    && printf '%s' "$WB_RND_BUILD_COMMIT" > "$IMAGE_COMMIT_PATH" \
    && chmod 0444 "$IMAGE_COMMIT_PATH"

EXPOSE 8000

CMD ["python", "scripts/start_inference_api.py"]
