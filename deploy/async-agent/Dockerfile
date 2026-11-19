FROM python:3.12.12-slim-bookworm@sha256:593bd06efe90efa80dc4eee3948be7c0fde4134606dd40d8dd8dbcade98e669c

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
COPY deploy/async-agent/requirements.txt /app/deployment/async-agent/requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --timeout 100 --no-deps -r deployment/async-agent/requirements.txt && pip check && \
    groupadd --system app && useradd --system --gid app --create-home app

COPY agent/ /app/agent/
COPY governance/ /app/governance/
COPY integrations/ /app/integrations/
COPY common/ /app/common/
COPY deploy/async-agent/aegra.json /app/deployment/async-agent/aegra.json
COPY deploy/async-agent/start.py /app/deployment/async-agent/start.py
COPY deploy/async-agent/compat.py /app/deployment/async-agent/compat.py
RUN python deployment/async-agent/compat.py
COPY deploy/async-agent/multitask_compat.py /app/deployment/async-agent/multitask_compat.py
RUN python deployment/async-agent/multitask_compat.py
ENV PYTHONPATH=/app AEGRA_CONFIG=/app/deployment/async-agent/aegra.json
USER app
EXPOSE 2026
CMD ["python", "deployment/async-agent/start.py"]
