#!/bin/sh
set -eu
if ! docker compose version >/dev/null 2>&1; then
  echo 'Potrzebne jest Docker Compose. Zainstaluj Docker z pluginem Compose i uruchom ponownie.' >&2
  exit 1
fi
if [ ! -f .env ]; then
  printf 'Domena aplikacji (np. starre.example.org): '
  read -r app_domain
  case "$app_domain" in
    *[!a-zA-Z0-9.-]*|''|.*|*.) echo 'Nieprawidłowa domena.' >&2;exit 1;;
  esac
  secret_values=$(python3 -c 'import secrets; print(secrets.token_urlsafe(64)); print(secrets.token_urlsafe(32))')
  secret_key=$(printf '%s\n' "$secret_values" | sed -n '1p')
  db_password=$(printf '%s\n' "$secret_values" | sed -n '2p')
  umask 077
  {
    printf 'DOMAIN=%s\n' "$app_domain"
    printf 'DJANGO_SECRET_KEY=%s\n' "$secret_key"
    printf 'POSTGRES_PASSWORD=%s\n' "$db_password"
    printf 'CONTACT_TO_EMAIL=\nCONTACT_FROM_EMAIL=\nSMTP_HOST=\nSMTP_PORT=587\nSMTP_USER=\nSMTP_PASSWORD=\nSMTP_TLS=1\n'
  } > .env
fi
docker compose up -d --build
printf '\nAplikacja uruchomiona. Gdy domena wskazuje na serwer, otwórz https://%s\n' "$(sed -n 's/^DOMAIN=//p' .env)"
printf 'Utwórz konto administratora: docker compose exec web python manage.py createsuperuser\n'
