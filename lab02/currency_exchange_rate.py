import argparse
import json
import logging
import os
from datetime import datetime
from pathlib import Path

import requests


API_URL = "http://localhost:8080"
MIN_DATE = datetime.strptime("2025-01-01", "%Y-%m-%d").date()
MAX_DATE = datetime.strptime("2025-09-15", "%Y-%m-%d").date()

# lab02/ este folderul scriptului.
SCRIPT_DIR = Path(__file__).resolve().parent

# Directorul părinte este rădăcina repository-ului automation.
PROJECT_ROOT = SCRIPT_DIR.parent

# data trebuie să fie în root-ul proiectului.
DATA_DIR = PROJECT_ROOT / "data"

# error.log trebuie să fie tot în root-ul proiectului.
LOG_FILE = PROJECT_ROOT / "error.log"


logging.basicConfig(
    filename=LOG_FILE,
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


def validate_date(date_string):
    """
    Verifică dacă data este în format YYYY-MM-DD
    și dacă aparține perioadei permise.
    """
    try:
        request_date = datetime.strptime(
            date_string,
            "%Y-%m-%d"
        ).date()
    except ValueError:
        raise ValueError(
            "Data trebuie să fie în format YYYY-MM-DD."
        )

    if request_date < MIN_DATE or request_date > MAX_DATE:
        raise ValueError(
            "Data trebuie să fie între 2025-01-01 și 2025-09-15."
        )

    return request_date


def get_exchange_rate(from_currency, to_currency, request_date):
    """
    Trimite cererea către API și întoarce răspunsul JSON.
    """

    api_key = os.getenv("API_KEY", "EXAMPLE_API_KEY")

    params = {
        "from": from_currency.upper(),
        "to": to_currency.upper(),
        "date": request_date
    }

    post_data = {
        "key": api_key
    }

    try:
        response = requests.post(
            API_URL,
            params=params,
            data=post_data,
            timeout=10
        )

        response.raise_for_status()

        result = response.json()

        if result.get("error"):
            raise ValueError(result["error"])

        return result

    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            "Nu se poate realiza conexiunea cu API-ul. "
            "Verifică dacă serviciul Docker rulează."
        )

    except requests.exceptions.Timeout:
        raise RuntimeError(
            "Cererea către API a expirat."
        )

    except requests.exceptions.RequestException as error:
        raise RuntimeError(
            f"Eroare la efectuarea cererii HTTP: {error}"
        )

    except json.JSONDecodeError:
        raise RuntimeError(
            "API-ul nu a returnat un răspuns JSON valid."
        )


def save_to_json(data, from_currency, to_currency, request_date):
    """
    Salvează răspunsul API într-un fișier JSON.
    """

    DATA_DIR.mkdir(exist_ok=True)

    filename = (
        f"{from_currency.upper()}_"
        f"{to_currency.upper()}_"
        f"{request_date}.json"
    )

    file_path = DATA_DIR / filename

    with open(file_path, "w", encoding="utf-8") as json_file:
        json.dump(
            data,
            json_file,
            indent=4,
            ensure_ascii=False
        )

    return file_path


def main():
    parser = argparse.ArgumentParser(
        description="Obține cursul valutar pentru o dată specificată."
    )

    parser.add_argument(
        "from_currency",
        help="Valuta sursă, de exemplu USD"
    )

    parser.add_argument(
        "to_currency",
        help="Valuta destinație, de exemplu EUR"
    )

    parser.add_argument(
        "date",
        help="Data în format YYYY-MM-DD"
    )

    args = parser.parse_args()

    try:
        validate_date(args.date)

        result = get_exchange_rate(
            args.from_currency,
            args.to_currency,
            args.date
        )

        file_path = save_to_json(
            result,
            args.from_currency,
            args.to_currency,
            args.date
        )

        print("Cererea a fost realizată cu succes.")
        print(
            f"{args.from_currency.upper()} -> "
            f"{args.to_currency.upper()}"
        )
        print(f"Data: {args.date}")
        print(f"Curs: {result['data']['rate']}")
        print(f"Date salvate în: {file_path}")

    except Exception as error:
        error_message = str(error)

        print(f"Eroare: {error_message}")

        logging.error(
            "%s -> %s, data %s: %s",
            args.from_currency,
            args.to_currency,
            args.date,
            error_message
        )


if __name__ == "__main__":
    main()
