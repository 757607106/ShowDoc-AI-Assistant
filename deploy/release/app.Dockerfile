FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/opt/playwright
WORKDIR /app

ARG PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
RUN pip download --no-deps --dest /tmp/torch --index-url https://download.pytorch.org/whl/cpu \
        torch==2.15.0+cpu torchvision==0.29.1+cpu \
    && pip install --no-cache-dir /tmp/torch/*.whl \
    && rm -r /tmp/torch

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN sed -i 's|http://deb.debian.org|https://mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update \
    && apt-get install -y --no-install-recommends libatomic1 \
    && python -m playwright install-deps chromium \
    && (PLAYWRIGHT_CHROMIUM_DOWNLOAD_HOST=https://registry.npmmirror.com/-/binary/playwright \
            python -m playwright install --only-shell chromium \
        || python -m playwright install --only-shell chromium) \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 showdoc \
    && install -d -o showdoc -g showdoc /data

RUN install -d -o showdoc -g showdoc /data/skill-bundles
COPY --chmod=755 . .
USER showdoc
CMD ["uvicorn", "asgi:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
