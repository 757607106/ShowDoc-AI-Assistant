FROM python:3.12-slim
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 libgomp1 \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch==2.15.0 torchvision==0.29.1
COPY attachment-parser-requirements.txt /opt/requirements.txt
RUN pip install --no-cache-dir -r /opt/requirements.txt
RUN docling-tools models download --output-dir /opt/docling-models layout tableformer rapidocr
ENV DOCLING_ARTIFACTS_PATH=/opt/docling-models HF_HUB_OFFLINE=1
COPY attachment-parser.py /opt/attachment-parser.py
USER 65534:65534
CMD ["sleep", "infinity"]
