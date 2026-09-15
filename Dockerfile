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

# pip is not needed at runtime. Uninstalling it also removes the vendored
# setuptools 70.3.0 that pip declares in its bundled SBOM (vendor.txt /
# bom.cdx.json), which security scanners report as vulnerable
# (CVE-2025-47273). Uninstalling is preferred over `rm` because it also
# removes the dist-info and the bin/pip* scripts.
RUN /app/.venv/bin/python -m pip uninstall -y pip


FROM base AS server

# Remove the pip that ships with the python base image, so the runtime image
# contains no importable pip. ensurepip is left in place: its bundled wheel
# embeds a pip copy, but it is not an installed package and scanners do not
# inspect inside it.
RUN /usr/local/bin/python -m pip uninstall -y pip

# The python base image pins libuuid 2.42.1-r0 (a .python-rundeps dependency),
# which carries several HIGH CVEs. A fixed version is available in the Alpine
# v3.24 main repo, so upgrade just that package instead of the whole base image.
RUN apk upgrade --no-cache libuuid

RUN adduser -u 1001 --disabled-password --gecos "" appuser
USER appuser

# Copy the sources and virtual env. No poetry.
COPY --chown=appuser --from=builder /app .
COPY --chown=appuser --from=builder /usr/share/nltk_data /usr/share/nltk_data

ENV PATH="/app/.venv/bin:$PATH"

ENV DEEPEVAL_TELEMETRY_OPT_OUT=1


EXPOSE 5000
CMD ["uvicorn", "aidial_admin_evaluation_metrics.main:app", "--host", "0.0.0.0", "--port", "5000"]
