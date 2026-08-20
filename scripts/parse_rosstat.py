"""Парсер XLSX Росстата для проекта «Что дорожает быстрее?»"""
from pathlib import Path
import json, sys
from openpyxl import load_workbook

MAPPING = {
 "gasoline95":{"name":"Бензин АИ-95","shortName":"Бензин","unit":"л","sourceName":"Бензин автомобильный марки АИ-95, л"},
 "eggs":{"name":"Яйца куриные","shortName":"Яйца","unit":"10 шт.","sourceName":"Яйца куриные, 10 шт."},
 "bread":{"name":"Хлеб пшеничный","shortName":"Хлеб","unit":"кг","sourceName":"Хлеб и булочные изделия из пшеничной муки различных сортов, кг"},
 "milk":{"name":"Молоко пастеризованное","shortName":"Молоко","unit":"л","sourceName":"Молоко питьевое цельное пастеризованное 2,5-3,2% жирности, л"},
 "potato":{"name":"Картофель","shortName":"Картофель","unit":"кг","sourceName":"Картофель, кг"},
 "bus":{"name":"Проезд в городском автобусе","shortName":"Автобус","unit":"поездка","sourceName":"Проезд в городском автобусе, поездка"}}
MONTHS={"января":"01","февраля":"02","марта":"03","апреля":"04","мая":"05","июня":"06","июля":"07","августа":"08","сентября":"09","октября":"10","ноября":"11","декабря":"12"}
def parse_header_date(text,year=2026):
 text=str(text).replace("**","").strip(); text=text[3:] if text.startswith("на ") else text; parts=text.split(); return f"{year}-{MONTHS[parts[1]]}-{int(parts[0]):02d}"
def main(src,dst):
 wb=load_workbook(src,data_only=True); ws=wb["2026"]
 dates=[parse_header_date(c.value) for c in ws[4][1:] if c.value]
 by_name={str(r[0].value).strip():[c.value for c in r[1:1+len(dates)]] for r in ws.iter_rows(min_row=5) if r[0].value}
 items=[]
 for item_id,meta in MAPPING.items():
  if meta["sourceName"] not in by_name: raise KeyError(f'Не найден показатель: {meta["sourceName"]}')
  items.append({"id":item_id,**meta,"indices":[float(v) for v in by_name[meta["sourceName"]]]})
 output={"source":"Росстат","sourceUrl":"https://rosstat.gov.ru/statistics/price","scope":"Российская Федерация","updated":dates[-1],"methodology":"Индексы потребительских цен в % к предыдущей дате регистрации. 7 дней = последняя недельная точка. 30 дней = накопленное изменение за последние 4 недельных интервала (28 дней).","dates":dates,"items":items}
 Path(dst).parent.mkdir(parents=True,exist_ok=True); Path(dst).write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding="utf-8"); print(f"Готово: {dst}")
if __name__=="__main__":
 if len(sys.argv)!=3: print("Использование: python scripts/parse_rosstat.py source/nedel_Ipc.xlsx data/prices.json"); raise SystemExit(1)
 main(sys.argv[1],sys.argv[2])
