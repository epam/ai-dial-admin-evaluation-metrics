FROM python:3.14-alpine AS base

WORKDIR /app

FROM base AS builder

RUN apk update && apk add build-base
RUN pip install poetry==2.2.1

# Install split into two steps (the dependencies and the sources)
# in order to leverage the Docker caching
COPY pyproject.toml poetry.lock poetry.toml ./
RUN poetry install --no-interaction --no-ansi --no-cache --no-root \
  --no-directory --only main

COPY . ./
RUN poetry install --no-interaction --no-ansi --no-cache --only main

# nltk punkt_tab is required for ai-dial-rag-eval
RUN poetry run python -m nltk.downloader -d /usr/share/nltk_data punkt_tab

# Download tiktoken model encodings into a cache dir so they are bundled in
# the image and not fetched from openaipublic.blob.core.windows.net at runtime.
ENV TIKTOKEN_CACHE_DIR=/app/tiktoken_cache
RUN .venv/bin/python -c "from tiktoken.model import (get_encoding as load, MODEL_TO_ENCODING as models); [(print(f'Loading tiktoken tokenizer {e}...'), load(e)) for e in set(models.values())]"


FROM base AS server

RUN adduser -u 1001 --disabled-password --gecos "" appuser
USER appuser

# Copy the sources and virtual env. No poetry.
COPY --chown=appuser --from=builder /app .
COPY --chown=appuser --from=builder /usr/share/nltk_data /usr/share/nltk_data

ENV PATH="/app/.venv/bin:$PATH"

ENV DEEPEVAL_TELEMETRY_OPT_OUT=1
ENV TIKTOKEN_CACHE_DIR=/app/tiktoken_cache


EXPOSE 5000
CMD ["uvicorn", "aidial_admin_evaluation_metrics.main:app", "--host", "0.0.0.0", "--port", "5000"]
