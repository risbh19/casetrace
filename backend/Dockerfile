FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 CORPUS_PATH=/project/data/law_corpus/sections.json
WORKDIR /project/backend
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr tesseract-ocr-eng tesseract-ocr-hin poppler-utils \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home appuser
COPY backend/ .
COPY data/ /project/data/
COPY scripts/ /project/scripts/
RUN python -m pip install --no-cache-dir --upgrade 'pip>=26.3,<27' \
    && pip install --no-cache-dir -r requirements.lock \
    && pip install --no-cache-dir --no-deps . && chown -R appuser:appuser /project
USER appuser
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
