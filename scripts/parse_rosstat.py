"""Парсер еженедельного XLSX Росстата для проекта «Что стало дороже?»."""
from pathlib import Path
import json
import sys
from openpyxl import load_workbook

MAPPING = {
    "gasoline95": {"name": "Бензин АИ-95", "shortName": "Бензин", "unit": "л", "sourceName": "Бензин автомобильный марки АИ-95, л"},
    "eggs": {"name": "Яйца куриные", "shortName": "Яйца", "unit": "10 шт.", "sourceName": "Яйца куриные, 10 шт."},
    "bread": {"name": "Хлеб пшеничный", "shortName": "Хлеб", "unit": "кг", "sourceName": "Хлеб и булочные изделия из пшеничной муки различных сортов, кг"},
    "milk": {"name": "Молоко пастеризованное", "shortName": "Молоко", "unit": "л", "sourceName": "Молоко питьевое цельное пастеризованное 2,5-3,2% жирности, л"},
    "potato": {"name": "Картофель", "shortName": "Картофель", "unit": "кг", "sourceName": "Картофель, кг"},
    "chicken": {"name": "Куры охлажденные и мороженые", "shortName": "Курица", "unit": "кг", "sourceName": "Куры охлажденные и мороженые, кг"},
}

MONTHS = {
    "января": "01", "февраля": "02", "марта": "03", "апреля": "04",
    "мая": "05", "июня": "06", "июля": "07", "августа": "08",
    "сентября": "09", "октября": "10", "ноября": "11", "декабря": "12",
}


def parse_header_date(text, year):
    text = str(text).replace("**", "").strip()
    if text.startswith("на "):
        text = text[3:]
    parts = text.split()
    if len(parts) < 2 or parts[1] not in MONTHS:
        raise ValueError(f"Не удалось распознать дату в заголовке: {text!r}")
    return f"{year}-{MONTHS[parts[1]]}-{int(parts[0]):02d}"


def main(src, dst):
    workbook = load_workbook(src, data_only=True)
    year_sheets = sorted((int(name) for name in workbook.sheetnames if str(name).isdigit() and len(str(name)) == 4))
    if not year_sheets:
        raise ValueError("В книге не найдены листы по годам")
    latest_year = year_sheets[-1]
    years = [year for year in year_sheets if year >= latest_year - 1]
    dates = []
    series = {item_id: [] for item_id in MAPPING}
    for year in years:
        worksheet = workbook[str(year)]
        columns = [(cell.column - 1, parse_header_date(cell.value, year)) for cell in worksheet[4][1:] if cell.value]
        by_name = {
            str(row[0].value).strip(): [cell.value for cell in row[1:]]
            for row in worksheet.iter_rows(min_row=5)
            if row[0].value
        }
        for index, date in columns:
            if dates and date <= dates[-1]:
                raise ValueError(f"Неверный порядок дат: {date}")
            dates.append(date)
            for item_id, meta in MAPPING.items():
                values = by_name.get(meta["sourceName"])
                if values is None or index >= len(values) or not isinstance(values[index], (int, float)):
                    raise ValueError(f"Нет индекса {meta['sourceName']} за {date}")
                series[item_id].append(float(values[index]))
    if len(dates) < 2:
        raise ValueError("Недостаточно недельных данных")
    items = [{"id": item_id, **meta, "indices": series[item_id]} for item_id, meta in MAPPING.items()]
    output = {
        "source": "Росстат",
        "sourceUrl": "https://rosstat.gov.ru/statistics/price",
        "scope": "Российская Федерация",
        "updated": dates[-1],
        "methodology": "Недельные индексы к предыдущей дате регистрации. 7 дней = последняя точка. 12 месяцев = накопленное изменение индексов после соответствующей даты год назад.",
        "dates": dates,
        "items": items,
    }
    destination = Path(dst)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Готово: {destination} · актуально на {dates[-1]}")
    return output


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Использование: python scripts/parse_rosstat.py source/nedel_Ipc.xlsx data/prices.json")
        raise SystemExit(1)
    main(sys.argv[1], sys.argv[2])
