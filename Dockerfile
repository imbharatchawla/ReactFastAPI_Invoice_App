FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000
ENV CHROMIUM_PATH=/usr/bin/chromium

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        chromium \
        fonts-liberation \
        fonts-dejavu-core \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/backend

COPY backend/requirements.txt ./requirements.txt

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY backend/ ./

COPY startup.sh /app/startup.sh

# Remove Windows CRLF and UTF-8 BOM.
RUN sed -i 's/\r$//' /app/startup.sh \
    && sed -i '1s/^\xEF\xBB\xBF//' /app/startup.sh \
    && chmod +x /app/startup.sh

EXPOSE 8000

# Calling the script through sh avoids executable-format/shebang issues.
CMD ["/bin/sh", "/app/startup.sh"]