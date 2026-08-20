"""Скачивает свежий еженедельный XLSX Росстата и обновляет data/prices.json."""
from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
import urllib3

from parse_rosstat import main as parse_xlsx

PAGE_URL = "https://rosstat.gov.ru/statistics/price"
SOURCE_DIR = Path("source")
SOURCE_FILE = SOURCE_DIR / "nedel_Ipc.xlsx"
OUTPUT_FILE = Path("data/prices.json")
HEADERS = {"User-Agent": "Mozilla/5.0 price-data-project/1.0"}

# На GitHub-hosted runner цепочка сертификатов rosstat.gov.ru иногда не проходит
# стандартную проверку CA. Отключаем TLS-проверку ТОЛЬКО для доменов Росстата;
# происхождение файла дополнительно ограничивается allowlist доменов и XLSX
# валидируется как ZIP-контейнер перед парсингом.
ALLOWED_HOSTS = {"rosstat.gov.ru", "www.rosstat.gov.ru"}
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def is_rosstat_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https" and parsed.hostname in ALLOWED_HOSTS


def rosstat_get(url: str, timeout: int) -> requests.Response:
    if not is_rosstat_url(url):
        raise ValueError(f"Заблокирован внешний источник: {url}")
    response = requests.get(url, timeout=timeout, headers=HEADERS, verify=False)
    response.raise_for_status()
    return response


def get_page() -> str:
    return rosstat_get(PAGE_URL, 45).text


def find_xlsx_urls(html: str) -> list[str]:
    hrefs = re.findall(r'href=["\']([^"\']+\.xlsx(?:\?[^"\']*)?)["\']', html, flags=re.I)
    urls = []
    for href in hrefs:
        url = urljoin(PAGE_URL, href.replace("&amp;", "&"))
        if is_rosstat_url(url) and url not in urls:
            urls.append(url)
    return urls


def score_url(url: str) -> int:
    low = url.lower()
    score = 0
    for token, points in (("nedel", 100), ("week", 80), ("ipc", 45), ("price", 20), ("cena", 20)):
        if token in low:
            score += points
    return score


def download(url: str, destination: Path) -> None:
    response = rosstat_get(url, 90)
    content = response.content
    if len(content) < 5000 or content[:2] != b"PK":
        raise ValueError("Ответ не похож на XLSX")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(content)


def main() -> None:
    html = get_page()
    urls = find_xlsx_urls(html)
    if not urls:
        raise RuntimeError("На странице Росстата не найдены ссылки на XLSX")

    candidates = sorted(urls, key=score_url, reverse=True)
    errors = []

    for url in candidates:
        try:
            print(f"Проверяем: {url}")
            download(url, SOURCE_FILE)
            parsed = parse_xlsx(SOURCE_FILE, OUTPUT_FILE)
            print(f"Данные обновлены: {parsed['updated']}")
            print(f"Источник XLSX: {url}")
            return
        except Exception as exc:
            errors.append(f"{url}: {exc}")
            print(f"Не подошёл: {exc}", file=sys.stderr)

    SOURCE_FILE.unlink(missing_ok=True)
    details = "\n".join(errors[:12])
    raise RuntimeError("Не удалось найти совместимый еженедельный XLSX Росстата.\n" + details)


if __name__ == "__main__":
    main()
