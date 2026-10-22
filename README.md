# systemZarzadzaniaZadaniami

## Opis projektu

Aplikacja webowa umożliwiająca dodawanie zadań, wyświetlanie listy i oznaczanie zadań jako wykonane.

## Technologie

- Python 3.12
- Flask
- Flask-SQLAlchemy
- MySQL 8.4
- Docker
- Docker Compose
- GitHub Actions
- pytest

## Wymagania

- Docker Desktop lub Docker Engine z Docker Compose
- Git

## Uruchomienie

1. Sklonuj repozytorium
2. Wypełnij plik .env danymi
3. Uruchom:
     docker compose up --build -d
4. Otwórz w przeglądarce:
     http://localhost:10101  (domyślnie ustawiony port)

## Funkcje aplikacji

- Dodawanie zadań.
- Wyświetlanie listy zadań.
- Ozaczanie zadań jako wykonane.
- Przechowywanie danych w MySQL.
- Sprawdzanie połączenia z bazą przez '/health'.

## Testy

Zainstaluj zależności:
pip install -r requirements.txt

Uruchom:
python -m pytest -v

lub

Uruchom:
docker compose run --rm web python -m pytest -v

## Docker

Budowanie i uruchamianie:
docker compose up --build -d

Logi aplikacji:
docker compose logs -f web

Status kontenerów:
docker compose ps

Zatrzymanie aplikacji:
docker compose down

Dane bazy są przechowywane w wolumenie 'mysql_data'.

## CI/CD

GitHub Actions automatycznie uruchamia testy i buduje obraz Docker po wysłaniu zmian do gałęzi 'main'.

## Trwałość danych

Dane MySQL są przechowywane w nazwanym wolumenie Docker.
Zatzymanie kontenerów bez usunięcia wolumenu nie usuwa danych bazy.


