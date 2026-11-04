FROM python:3.11-slim-bookworm

# Microsoft ODBC Driver 18 for SQL Server (required by pyodbc)
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl gnupg ca-certificates \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && echo "deb [arch=amd64,arm64 signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" \
       > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 unixodbc \
    && apt-get purge -y curl gnupg && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini docker-entrypoint.sh ./
COPY alembic ./alembic
COPY app ./app

# Run as an unprivileged user: AI-generated tests execute inside this container
RUN useradd --create-home --uid 10001 devteam \
    && mkdir -p /data/workspaces && chown -R devteam /data /app \
    && chmod +x docker-entrypoint.sh
USER devteam

EXPOSE 8000
ENTRYPOINT ["./docker-entrypoint.sh"]
