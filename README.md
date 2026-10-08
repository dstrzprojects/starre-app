# Berea — strona i aplikacja na telefon

Ta paczka zawiera Angular (interfejs HTML), Django (logowanie i API), PostgreSQL oraz konfigurację PWA. Zawiera kod źródłowy i zbudowany interfejs; serwer z Docker Compose zbuduje go ponownie podczas instalacji.

## Uruchomienie na serwerze Linux

Potrzebujesz domeny wskazującej na serwer, Docker z `docker compose` oraz wolnych portów 80 i 443. Rozpakuj paczkę w wybranym katalogu i uruchom:

```bash
cd starre-app
./install.sh
```

Podaj domenę. Skrypt wygeneruje hasło bazy i klucz aplikacji w lokalnym pliku `.env`, uruchomi PostgreSQL, Django i Caddy. Caddy pobierze certyfikat HTTPS, gdy domena wskazuje na ten serwer. Następnie utwórz administratora:

```bash
docker compose exec web python manage.py createsuperuser
```

W panelu `https://TWOJA-DOMENA/admin/` zakładki „Kontakt” i „Wsparcie” są osobnymi pozycjami, każda ma przyciski „Dodaj” i „Zmień”. Wejdź w „Zmień” i użyj checkboxa przy danej pozycji, aby ukryć ją użytkownikom. Checkboxy dla Startu, Ogłoszeń, Spotkań, Finansów i Grafiku znajdziesz w „Pozostałe zakładki”. Ukrycie zmienia tylko widoczność przycisku nawigacji. Użytkownicy tworzą konta przez stronę. Moderatorowi nadaj w panelu opcję `Staff status` (bez `Superuser status`). Moderator może usuwać cudze ogłoszenia, ale nie edytuje ich i nie zarządza użytkownikami. Konto administratora ma dostęp do panelu.

Superuser może też otworzyć w aplikacji **Konto → Ustawienia aplikacji**, aby edytować kontakt, dane przelewu, wsparcie i widoczność zakładek bez wchodzenia do Django Admin. Adres odbiorcy wiadomości kontaktowych zapisuje się w bazie. Dane serwera SMTP nadal pozostają w `.env`. Uprawnienia superusera nie pozwalają edytować cudzych wydarzeń ani ogłoszeń; ich autor może zmieniać tylko własne wpisy.

### Wariant z Nginx na serwerze

Jeśli serwer ma już Nginx i certyfikat HTTPS, uruchom wariant z Nginx:

```bash
docker compose -f compose.yaml -f compose.nginx.yaml --profile nginx up -d --build
```

Skopiuj `deploy/nginx/host.conf.example` do konfiguracji witryny Nginx. Zastąp `TWOJA-DOMENA` domeną i sprawdź ścieżki certyfikatu TLS. Potem sprawdź konfigurację (`nginx -t`) i przeładuj Nginx. Nginx serwera obsługuje HTTPS, kontener Nginx na localhost:8080 przekazuje żądania do Django i podaje zdjęcia. Nie uruchamiaj domyślnego Caddy na portach 80/443 równocześnie z Nginx serwera.

Dane kontaktowe SMTP są opcjonalne. Aby uruchomić formularz, wpisz do `.env` `CONTACT_TO_EMAIL`, `CONTACT_FROM_EMAIL`, `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`, ewentualnie port i TLS. Po zmianie:

```bash
docker compose up -d --force-recreate web
```

## Skrót na telefonie

Otwórz stronę przez HTTPS i użyj „Dodaj Berea na ekran telefonu”. Na iPhonie wybierz w Safari „Udostępnij” → „Dodaj do ekranu początkowego”. Na Androidzie przeglądarka może pokazać „Zainstaluj aplikację”. PWA zapisuje interfejs do szybkiego uruchomienia, ale aktualne spotkania i zapisy wymagają połączenia z internetem.

## Aktualizacja i kopia danych

Po przesłaniu nowej wersji plików uruchom `docker compose up -d --build`. Dane są w wolumenie `postgres_data`, a zdjęcia w `media_data`; nie kasuj ich przy aktualizacji. Przed aktualizacją wykonaj kopię:

```bash
docker compose exec -T db pg_dump -U starre starre > starre-backup.sql
```

Przechowuj też kopię zdjęć i pliku `.env` w bezpiecznym miejscu. Nie publikuj `.env` ani kopii bazy w katalogu strony.

Ta wersja zawiera migracje danych kontaktowych, widoczności zakładek oraz tabeli limitów żądań. Kontener `web` wykona je przy starcie. Obrazy przesłane po aktualizacji są sprawdzane i ponownie kodowane jako JPG; wcześniejsze pliki pozostają na dysku. Warto przejrzeć wcześniej przesłane obrazy przed publicznym otwarciem strony.

Logowanie, rejestracja, wysyłanie wiadomości, zapisy, edycja treści i zdjęcia mają limity prób. Listy wydarzeń i ogłoszeń pobierają po 60 wpisów i oferują przycisk do wczytania kolejnych. Środowisko produkcyjne wymaga aktualnych zależności z `requirements.txt`, poprawnej domeny HTTPS i silnych sekretów w `.env`. Nie wystawiaj portu PostgreSQL ani kontenera Django bezpośrednio do internetu. Zadbaj o regularne kopie bazy i zdjęć.

## Zakres pierwszej wersji

Działają: konto z hasłem, profil, ogłoszenia, spotkania ze zdjęciem, zapisy z kontem i anonimowe, zadania dla wielu osób, cele zbiórek i dane przelewów, panel administratora, powiadomienie o usunięciu cudzego ogłoszenia, formularz kontaktowy po skonfigurowaniu SMTP. Płatności wykonuje użytkownik w banku; aplikacja nie obsługuje transakcji i nie śledzi postępu zbiórki.

Ta wersja nie wysyła powiadomień push i nie obsługuje edycji wydarzeń bez połączenia. Przed publicznym uruchomieniem ustaw domenę i wykonaj próbny zapis dwoma kontami. Część zawartości z prototypu (w tym demonstracyjne konta i wydarzenia) nie jest automatycznie importowana; dodaj ją przez stronę i panel admina.

## Lokalna weryfikacja kodu

Frontend: `cd frontend && npm ci && npm run build`. Backend: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`, potem `cd backend && DB_ENGINE=sqlite DJANGO_DEBUG=1 ../.venv/bin/python manage.py test core`. Tryb SQLite służy wyłącznie testom lokalnym; instalacja serwerowa używa PostgreSQL.

## Nowy układ na komputerze

Przy szerokości od 1024 px aplikacja wyświetla boczną nawigację, karty w kolumnach, dwupanelowe szczegóły wydarzenia i szersze formularze. Na telefonie zachowuje dotychczasowy układ.

### Aktualizacja istniejącej wersji na Windows

Rozpakuj zawartość folderu `starre-app` z tej paczki do istniejącego folderu `starre-app`, zastępując pliki aplikacji. Zachowaj swój `compose.local.yaml` oraz `.env`. Nie zmieniaj nazwy folderu ani nie usuwaj wolumenów Docker — Twoje konta i wpisy pozostaną w dotychczasowej bazie.

W PowerShellu otwartym w tym folderze wykonaj:

```powershell
docker compose -f compose.local.yaml up -d --build
```

Po zakończeniu otwórz http://localhost:8000/ w nowym oknie prywatnym. Jeżeli zwykłe okno pokazuje poprzednią wersję, usuń dane witryny localhost w przeglądarce i ponownie otwórz stronę (wyloguje to konto, ale nie usuwa danych w bazie).

Wydarzenie ma opcjonalne pole „Podsumowanie tematu”; jeśli pozostawisz je puste, sekcja nie pokaże się uczestnikom.
