FROM node:24-alpine AS frontend
WORKDIR /work
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
COPY --from=frontend /work/dist/frontend/browser/ /app/frontend/browser/
RUN DJANGO_DEBUG=1 python manage.py collectstatic --noinput
RUN adduser --disabled-password --gecos '' appuser && mkdir -p /app/media && chown -R appuser:appuser /app
USER appuser
EXPOSE 8000
CMD ["sh","-c","python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 2 --access-logfile -"]
