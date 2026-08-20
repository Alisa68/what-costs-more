"""Скачивает свежий еженедельный XLSX Росстата и обновляет data/prices.json."""
from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import urljoin

import requests

from parse_rosstat import main as parse_xlsx

PAGE_URL = "https://rosstat.gov.ru/statistics/price"
SOURCE_DIR = Path("source")
SOURCE_FILE = SOURCE_DIR / "nedel_Ipc.xlsx"
OUTPUT_FILE = Path("data/prices.json")


def get_page() -> str:
    response = requests.get(
        PAGE_URL,
        timeout=45,
        headers={"User-Agent": "Mozilla/5.0 price-data-project/1.0"},
    )
    response.raise_for_status()
    return response.text


def find_xlsx_urls(html: str) -> list[str]:
    hrefs = re.findall(r'href=["\']([^"\']+\.xlsx(?:\?[^"\']*)?)["\']', html, flags=re.I)
    urls = []
    for href in hrefs:
        url = urljoin(PAGE_URL, href.replace("&amp;", "&"))
        if url not in urls:
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
    response = requests.get(
        url,
        timeout=90,
        headers={"User-Agent": "Mozilla/5.0 price-data-project/1.0"},
    )
    response.raise_for_status()
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
