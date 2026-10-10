#!/usr/bin/env python3
"""Find and download current-year Minenergo IPR orders for listed Rosseti companies."""

from __future__ import annotations

import argparse
import gzip
import html
import json
import os
import re
import shutil
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
import zlib
import zipfile
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from xml.etree import ElementTree as ET

MAIN_PAGE = "https://minenergo.gov.ru/industries/power-industry/investment-programs"
SITE = "https://minenergo.gov.ru"
MOEX_ISS = "https://iss.moex.com/iss"
DIRECT_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
INSECURE_DIRECT_OPENER = urllib.request.build_opener(
    urllib.request.ProxyHandler({}),
    urllib.request.HTTPSHandler(context=ssl._create_unverified_context()),
)
RSBU_PAGE = "https://www.rossetivolga.ru/ru/aktsioneram_i_investoram/raskritie_informatsii_obcshestvom_i_otchetnaya_informatsiya/finansovaya_%28buhgalterskaya%29_otchetnost_po_rsbu"
MOEX_COMPANIES = {
    "pao_federalnaya_setevaya_kompaniya_rosseti": "FEES",
    "pao_rosseti_volga": "MRKV",
    "pao_rosseti_tsentr": "MRKC",
    "pao_rosseti_tsentr_i_privolzhe": "MRKP",
    "pao_rosseti_lenenergo": "LSNG",
    "pao_rosseti_moskovskiy_region": "MSRS",
    "pao_rosseti_severo_zapad_ranee_pao_mrsk_severo_zapada_": "MRKZ",
    "pao_rosseti_sibir": "MRKS",
    "pao_rosseti_ural": "MRKU",
    "pao_rosseti_yug": "MRKY",
}
MOEX_TICKER_ALIASES = {"pao_rosseti_lenenergo": ("LSNGP",)}
DATE_RE = re.compile(r"(?:дата\s+публикации|опубликовано)\s*:?[\s№-]*(\d{1,2}\.\d{1,2}\.\d{4})", re.I)
TITLE_RE = re.compile(r"Приказ\s+Минэнерго\s+(?:России|РФ)[^\n]{0,700}", re.I)
HREF_RE = re.compile(r"<a\b[^>]*?\bhref\s*=\s*(['\"])(.*?)\1[^>]*>(.*?)</a\s*>", re.I | re.S)
ANY_HREF_RE = re.compile(r"\bhref\s*=\s*(['\"])(.*?)\1", re.I | re.S)
OPTION_RE = re.compile(r"<option\b[^>]*?(?:value|data-url)\s*=\s*(['\"])(.*?)\1[^>]*>(.*?)</option\s*>", re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>")


@dataclass
class Company:
    name: str
    url: str
    ticker: str


@dataclass
class Order:
    company: Company
    title: str
    publication_date: date
    document_url: str


@dataclass
class ApiCompany:
    name: str
    code: str
    ticker: str
    ticker_aliases: tuple[str, ...] = ()

    @property
    def tickers(self) -> tuple[str, ...]:
        return (self.ticker, *self.ticker_aliases)


def fallback_companies() -> list[Company]:
    """Use the same catalog when Minenergo renders the dropdown via JavaScript."""
    return [
        Company(slug.replace("_", " ").title(), f"{MAIN_PAGE}/{slug}", ticker)
        for slug, ticker in MOEX_COMPANIES.items()
    ]


def api_get(action: str, timeout: int, **params):
    query = urllib.parse.urlencode({"action": action, "lang": "ru", **params})
    response = fetch(f"{SITE}/api/v1/?{query}", timeout)
    if isinstance(response, bytes):
        response = response.decode("utf-8", errors="replace")
    return json.loads(response)


def api_companies(timeout: int) -> list[ApiCompany]:
    data = api_get("organizations.getItemsShort", timeout)
    result = []
    for item in data if isinstance(data, list) else data.get("items", []):
        if item.get("sectionName") == "ДЗО/ВЗО ПАО «Россети»" and item.get("code") in MOEX_COMPANIES:
            code = item["code"]
            result.append(ApiCompany(
                item.get("name", code), code, MOEX_COMPANIES[code], MOEX_TICKER_ALIASES.get(code, ())
            ))
    return result


def api_order(company: ApiCompany, payload, year: int) -> tuple[str, str, str, str] | None:
    """Find (title, date, document URL, filename) in the investment-program group."""
    wanted_group = "информация о проектах инвестиционных программ"

    def normalized(value) -> str:
        value = html.unescape(str(value or "")).replace("\\u0026nbsp;", " ").replace("\xa0", " ")
        return re.sub(r"\s+", " ", value).strip()
    groups = []

    def walk(value):
        if isinstance(value, dict):
            if "files" in value and wanted_group in normalized(value.get("name")).lower():
                groups.append(value)
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(payload)
    candidates = []
    for group in groups:
        for file in group.get("files", []):
            description = normalized(file.get("description"))
            title = normalized(file.get("name"))
            searchable = f"{description} {title}"
            if not re.search(r"приказ\s+минэнерго\s+россии", searchable, re.I):
                continue
            date_match = re.search(r"дата\s+публикации\s*:?\s*(\d{1,2}\.\d{1,2}\.\d{4})", searchable, re.I)
            if not date_match and isinstance(file.get("date"), list) and len(file["date"]) > 1:
                date_match = re.search(r"(\d{1,2}\.\d{1,2}\.\d{4})", normalized(file["date"][1]))
            if not date_match:
                continue
            day, month, published_year = (int(part) for part in date_match.group(1).split("."))
            if published_year != year:
                continue
            candidates.append((date(published_year, month, day), description, file.get("src", ""), title))
    if not candidates:
        return None
    published, description, src, filename = max(candidates, key=lambda item: item[0])
    return description, published.strftime("%d.%m.%Y"), urllib.parse.urljoin(SITE, src), filename


def fetch(url: str, timeout: int) -> str | bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "Energo-Rosseti-IPR/1.0", "Accept": "text/html,application/pdf,application/zip,*/*"})
    try:
        response_context = DIRECT_OPENER.open(request, timeout=timeout)
    except urllib.error.URLError as direct_error:
        if not isinstance(direct_error.reason, ssl.SSLCertVerificationError):
            raise
        print(f"SSL-сертификат {url} не прошёл проверку; повтор прямого запроса без проверки сертификата", file=sys.stderr)
        response_context = INSECURE_DIRECT_OPENER.open(request, timeout=timeout)
    with response_context as response:
        data = response.read()
        encoding = (response.headers.get("Content-Encoding") or "").lower()
        if encoding == "gzip":
            data = gzip.decompress(data)
        elif encoding == "deflate":
            data = zlib.decompress(data)
        if response.headers.get_content_type() != "text/html":
            return data
        charset = response.headers.get_content_charset() or "utf-8"
        try:
            return data.decode(charset, errors="replace")
        except LookupError:
            return data.decode("utf-8", errors="replace")


def moex_history(ticker: str, publication_date: date, timeout: int) -> list[dict]:
    """Return nearby daily MOEX candles, including the next trading day."""
    start = publication_date - timedelta(days=2)
    end = publication_date + timedelta(days=4)
    query = urllib.parse.urlencode({
        "from": start.isoformat(),
        "till": end.isoformat(),
        "iss.meta": "off",
    })
    url = f"{MOEX_ISS}/history/engines/stock/markets/shares/boards/TQBR/securities/{ticker}.json?{query}"
    payload = fetch(url, timeout)
    if isinstance(payload, bytes):
        payload = payload.decode("utf-8", errors="replace")
    data = json.loads(payload)
    block = data.get("history", {})
    columns = block.get("columns", [])
    rows = [dict(zip(columns, row)) for row in block.get("data", [])]
    rows.sort(key=lambda row: row.get("TRADEDATE") or "")
    return rows


def print_market_window(ticker: str, publication_date_text: str, timeout: int) -> None:
    """Print the publication day and adjacent trading days for a MOEX ticker."""
    publication_date = date.fromisoformat("-".join(reversed(publication_date_text.split("."))))
    rows = moex_history(ticker, publication_date, timeout)
    publication_iso = publication_date.isoformat()
    publication_index = next(
        (index for index, row in enumerate(rows) if row.get("TRADEDATE") == publication_iso),
        None,
    )
    if publication_index is None:
        print("  Данные MOEX за этот период не найдены")
        return
    nearby_indexes = set(range(max(0, publication_index - 1), min(len(rows), publication_index + 2)))
    previous_close = None
    print("  Динамика акций на MOEX (TQBR):")
    printed = 0
    for index, row in enumerate(rows):
        trade_date = row.get("TRADEDATE")
        close = row.get("CLOSE") or row.get("LEGALCLOSEPRICE")
        if index not in nearby_indexes:
            if close is not None:
                previous_close = float(close)
            continue
        change = None
        if close is not None and previous_close not in (None, 0):
            change = (float(close) / previous_close - 1) * 100
        print(
            f"    {trade_date}: открытие={row.get('OPEN')}, максимум={row.get('HIGH')}, "
            f"минимум={row.get('LOW')}, закрытие={close}, объём={row.get('VOLUME')}"
            + (f", к предыдущему дню={change:+.2f}%" if change is not None else "")
        )
        printed += 1
        if close is not None:
            previous_close = float(close)
    if not printed:
        print("    Данные MOEX за этот период не найдены")


def download_rsbu_q3(year: int, output: Path, timeout: int) -> Path:
    """Find and download Rosseti Volga's RAS report for Q3 of the year."""
    page = fetch(RSBU_PAGE, timeout)
    if isinstance(page, bytes):
        page = page.decode("utf-8", errors="replace")
    wanted = re.compile(
        rf"бухгалтерская\s+отчетность\s+за\s*3\s*квартал\s*{year}\s*года",
        re.I,
    )
    candidates = []
    for href, anchor, _nearby in links(page):
        if wanted.search(anchor):
            candidates.append(urllib.parse.urljoin(RSBU_PAGE, href))
    if not candidates:
        # The current site wraps the link title in nested elements, so the
        # strict <a>...</a> parser may not capture the whole anchor text.
        title_match = wanted.search(page)
        if title_match:
            window_start = max(0, title_match.start() - 3000)
            window_end = min(len(page), title_match.end() + 3000)
            window = page[window_start:window_end]
            href_matches = list(ANY_HREF_RE.finditer(window))
            pdf_matches = [
                match for match in href_matches
                if re.search(r"\.pdf(?:$|[?#])", html.unescape(match.group(2)), re.I)
            ]
            if pdf_matches:
                nearest = min(pdf_matches, key=lambda match: abs(match.start() - (title_match.start() - window_start)))
                candidates.append(urllib.parse.urljoin(RSBU_PAGE, html.unescape(nearest.group(2)).strip()))
    if not candidates:
        known_urls = {
            2025: "https://www.rossetivolga.ru/i/files/2025/10/29/buhgalterskaya_otchetnost_za_yanvar_sentyabr_2025.pdf",
        }
        if year in known_urls:
            candidates.append(known_urls[year])
    if not candidates:
        raise RuntimeError(f"отчёт за 3 квартал {year} года на сайте Россети Волга не найден")
    document_url = candidates[0]
    content = fetch(document_url, timeout)
    if isinstance(content, str):
        content = content.encode("utf-8")
    output.mkdir(parents=True, exist_ok=True)
    filename = Path(urllib.parse.urlparse(document_url).path).name or f"rosseti_volga_rsbu_q3_{year}.pdf"
    if not filename.lower().endswith(".pdf"):
        filename += ".pdf"
    target = output / f"Россети_Волга_Бухгалтерская_отчетность_3_квартал_{year}.pdf"
    target.write_bytes(content)
    print(f"  РСБУ за 3 квартал {year} года: {target}")
    print(f"  Ссылка на РСБУ: {document_url}")
    return target


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(TAG_RE.sub(" ", value))).strip()


def links(page: str) -> list[tuple[str, str, str]]:
    result = []
    for match in HREF_RE.finditer(page):
        href, anchor = html.unescape(match.group(2)).strip(), clean_text(match.group(3))
        before = clean_text(page[max(0, match.start() - 12000):match.start()])
        after = clean_text(page[match.end():match.end() + 3000])
        result.append((href, anchor, f"{before}\n{anchor}\n{after}"))
    return result


def dropdown_options(page: str) -> list[tuple[str, str, str]]:
    result = []
    for match in OPTION_RE.finditer(page):
        value, label = html.unescape(match.group(2)).strip(), clean_text(match.group(3))
        result.append((value, label, label))
    return result


def find_companies(main_html: str) -> list[Company]:
    result, seen = [], set()
    all_links = links(main_html) + dropdown_options(main_html)
    for href, anchor, nearby in all_links:
        absolute = urllib.parse.urljoin(MAIN_PAGE + "/", href)
        parts = [part for part in urllib.parse.urlparse(absolute).path.rstrip("/").split("/") if part]
        if len(parts) >= 2 and parts[-2] == "investment-programs":
            slug = parts[-1].lower()
        else:
            # Some versions of the main page put only the company slug in <option value>.
            slug = href.strip("/").split("/")[-1].lower()
            absolute = urllib.parse.urljoin(MAIN_PAGE + "/", slug)
        ticker = MOEX_COMPANIES.get(slug)
        if not ticker or slug in seen or "россет" not in (anchor + nearby).lower():
            continue
        seen.add(slug)
        result.append(Company(anchor or slug.replace("_", " ").title(), absolute, ticker))
    return sorted(result, key=lambda item: item.name)


def find_order(company: Company, page: str, year: int) -> Order | None:
    candidates = []
    parsed_links = links(page)
    for href, _anchor, nearby in parsed_links:
        title_match, date_match = TITLE_RE.search(nearby), DATE_RE.search(nearby)
        if not title_match or not date_match:
            continue
        day, month, published_year = (int(part) for part in date_match.group(1).split("."))
        if published_year != year:
            continue
        try:
            published = date(published_year, month, day)
        except ValueError:
            continue
        candidates.append(Order(company, clean_text(title_match.group(0)), published, urllib.parse.urljoin(company.url, href)))
    if candidates:
        return max(candidates, key=lambda item: item.publication_date)

    # Fallback for the current Minenergo markup: the document title and date
    # are rendered in a card, while the download URL is placed in a separate
    # nested element. Associate the first current-year card with the nearest
    # PDF/ZIP link from the same result page.
    text = clean_text(page)
    title_match = TITLE_RE.search(text)
    if title_match:
        date_match = DATE_RE.search(text, title_match.end()) or DATE_RE.search(text)
        if date_match:
            day, month, published_year = (int(part) for part in date_match.group(1).split("."))
            if published_year == year:
                try:
                    published = date(published_year, month, day)
                except ValueError:
                    return None
                download_links = []
                for match in ANY_HREF_RE.finditer(page):
                    href = html.unescape(match.group(2)).strip()
                    if re.search(r"\.(?:pdf|zip|xlsx?|docx?)(?:$|[?#])", href, re.I) or "/upload2/" in href:
                        download_links.append(urllib.parse.urljoin(company.url, href))
                if download_links:
                    return Order(company, clean_text(title_match.group(0)), published, download_links[0])
    return None


def filtered_company_url(company: Company) -> str:
    # This is the same filter used by the Minenergo UI: it searches the
    # document list by the word "приказ" and sorts newest documents first.
    query = urllib.parse.urlencode({"query": "приказ", "sortOrder": "desc"})
    return f"{company.url}?{query}"


def save(order: Order, content: bytes, output: Path) -> Path:
    output.mkdir(parents=True, exist_ok=True)
    suffix = Path(urllib.parse.urlparse(order.document_url).path).suffix or ".bin"
    name = re.sub(r"[^\wА-Яа-яЁё.-]+", "_", order.company.name).strip("_")
    path = output / f"{name}_{order.publication_date.isoformat()}{suffix}"
    path.write_bytes(content)
    return path


def save_api_document(company: ApiCompany, publication_date: str, filename: str, url: str, content: bytes, output: Path) -> Path:
    output.mkdir(parents=True, exist_ok=True)
    safe_company = re.sub(r"[^\wА-Яа-яЁё.-]+", "_", company.name).strip("_")
    safe_filename = re.sub(r"[^\wА-Яа-яЁё.-]+", "_", filename).strip("_")
    suffix = Path(urllib.parse.urlparse(url).path).suffix or Path(safe_filename).suffix or ".bin"
    if not safe_filename.lower().endswith(suffix.lower()):
        safe_filename += suffix
    path = output / f"{safe_company}_{publication_date.replace('.', '-')}_{safe_filename}"
    path.write_bytes(content)
    return path


def xlsx_to_text(path: Path, max_rows: int = 20000) -> str:
    """Convert an XLSX workbook to compact tabular text without extra packages."""
    with zipfile.ZipFile(path) as workbook:
        names = set(workbook.namelist())
        shared = []
        if "xl/sharedStrings.xml" in names:
            root = ET.fromstring(workbook.read("xl/sharedStrings.xml"))
            shared = ["".join(node.itertext()) for node in root]
        sheets = sorted(name for name in names if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", name))
        output = [f"Файл: {path.name}"]
        total = 0
        for sheet_name in sheets:
            root = ET.fromstring(workbook.read(sheet_name))
            output.append(f"\nЛист: {sheet_name.rsplit('/', 1)[-1]}")
            for row in root.findall(".//{*}row"):
                values = []
                for cell in row.findall("{*}c"):
                    value = cell.find("{*}v")
                    text = "" if value is None else value.text or ""
                    if cell.attrib.get("t") == "s" and text.isdigit() and int(text) < len(shared):
                        text = shared[int(text)]
                    if cell.attrib.get("t") == "inlineStr":
                        inline = cell.find("{*}is")
                        text = "" if inline is None else "".join(inline.itertext())
                    values.append(text.replace("\t", " ").replace("\n", " "))
                if values:
                    output.append("\t".join(values))
                    total += 1
                    if total >= max_rows:
                        output.append(f"\n[Обрезано после {max_rows} строк]")
                        return "\n".join(output)
    return "\n".join(output)


def xlsx_sheet_names(path: Path) -> list[str]:
    """Return visible worksheet names from workbook.xml in their original order."""
    with zipfile.ZipFile(path) as workbook:
        try:
            root = ET.fromstring(workbook.read("xl/workbook.xml"))
        except KeyError:
            return []
        return [sheet.attrib.get("name", "") for sheet in root.findall(".//{*}sheet")]


def analyze_with_yandex(text: str, file_name: str) -> str:
    """Analyze workbook text using the same YandexGPT setup as smart_home_service."""
    api_key = os.getenv("YANDEX_AI_KEY")
    folder = os.getenv("YANDEX_CLOUD_FOLDER")
    if not api_key or not folder:
        raise RuntimeError("задайте переменные окружения YANDEX_AI_KEY и YANDEX_CLOUD_FOLDER")
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("установите пакет openai: python -m pip install openai") from exc
    client = OpenAI(api_key=api_key, base_url="https://ai.api.cloud.yandex.net/v1", project=folder)
    instructions = (
        "Ты аналитик инвестиционных программ электросетевых компаний. "
        "Проанализируй таблицу ИПР и верни ответ на русском языке. "
        "Выдели: 1) общую сумму инвестиций по годам, если она есть; "
        "2) крупнейшие проекты и мероприятия; 3) источники финансирования; "
        "4) заметные изменения и риски. Не выдумывай отсутствующие значения; "
        "если структура листа непонятна, укажи это. Используй четкие заголовки и таблицы Markdown."
    )
    response = client.responses.create(
        model=f"gpt://{folder}/yandexgpt-5-lite/latest",
        temperature=0.1,
        instructions=instructions,
        input=f"Файл инвестиционной программы: {file_name}\n\n{text[:120000]}",
        max_output_tokens=5000,
    )
    return response.output_text


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip().strip("\"'")
        os.environ.setdefault(key, value)


def extract_and_analyze(zip_path: Path, output: Path, analyze: bool, print_excel: bool, list_sheets: bool) -> None:
    extract_dir = output / "extracted" / zip_path.stem
    extract_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as archive:
        xlsx_members = [info for info in archive.infolist() if info.filename.lower().endswith((".xlsx", ".xlsm"))]
        if not xlsx_members:
            print("  Excel-файлы в архиве не найдены")
            return
        for info in xlsx_members:
            target = extract_dir / Path(info.filename).name
            with archive.open(info) as source, target.open("wb") as destination:
                shutil.copyfileobj(source, destination)
            print(f"  Excel: {target}")
            if list_sheets:
                sheet_names = xlsx_sheet_names(target)
                print("  Листы:")
                for index, sheet_name in enumerate(sheet_names, 1):
                    print(f"    {index}. {sheet_name}")
                if not sheet_names:
                    print("    Не удалось определить названия листов")
                continue
            workbook_text = xlsx_to_text(target)
            if print_excel or analyze:
                print(f"\n===== НАЧАЛО ДАННЫХ EXCEL: {target.name} =====")
                print(workbook_text)
                print(f"===== КОНЕЦ ДАННЫХ EXCEL: {target.name} =====\n")
            if analyze:
                print(f"  Отправляю {target.name} в YandexGPT...")
                analysis = analyze_with_yandex(workbook_text, target.name)
                analysis_path = target.with_suffix(target.suffix + ".analysis.md")
                analysis_path.write_text(analysis, encoding="utf-8")
                print(f"  Анализ сохранён: {analysis_path}\n")
                print(analysis)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, default=date.today().year)
    parser.add_argument("--company", help="Проверить одну компанию по slug или тикеру")
    parser.add_argument("--debug", action="store_true", help="Сохранить HTML страниц для диагностики")
    parser.add_argument("--analyze", action="store_true", help="Распаковать Excel и отправить его в YandexGPT")
    parser.add_argument("--print-excel", action="store_true", help="Вывести в консоль все данные Excel, но не отправлять их в YandexGPT")
    parser.add_argument("--list-sheets", action="store_true", help="Вывести только названия листов Excel")
    parser.add_argument("--download-rsbu", action="store_true", help="Скачать бухгалтерскую отчетность Россети Волга за 3 квартал")
    parser.add_argument("--rsbu-year", type=int, help="Год отчётности РСБУ; по умолчанию совпадает с --year")
    parser.add_argument("--env-file", type=Path, default=Path(__file__).resolve().parent.parent / "smart_home_service" / ".env")
    parser.add_argument("--out", type=Path, default=Path("data/rosseti_ipr_orders"))
    parser.add_argument("--timeout", type=int, default=45)
    args = parser.parse_args()
    load_env_file(args.env_file)
    try:
        companies = api_companies(args.timeout)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Не удалось получить список компаний через API: {exc}", file=sys.stderr)
        return 1
    if not companies:
        print("В API не найдены компании из группы ДЗО/ВЗО ПАО «Россети».", file=sys.stderr)
        return 2
    if args.company:
        needle = args.company.lower()
        companies = [
            company for company in companies
            if needle in company.code.lower() or needle in {ticker.lower() for ticker in company.tickers}
        ]
        for company in companies:
            matching_ticker = next((ticker for ticker in company.tickers if ticker.lower() == needle), None)
            if matching_ticker:
                company.ticker = matching_ticker
        if not companies:
            print(f"Компания не найдена: {args.company}", file=sys.stderr)
            return 2
    print(f"Компаний найдено: {len(companies)}; год публикации: {args.year}\n")
    found = 0
    for company in companies:
        print(f"[{company.ticker}] {company.name} ({company.code})")
        try:
            payload = api_get("organizations.getItemDetail", args.timeout, code=company.code)
            order = api_order(company, payload, args.year)
            if order is None:
                print("  Приказ за указанный год не найден\n")
                continue
            description, publication_date, document_url, filename = order
            print(f"  Дата публикации: {publication_date}")
            print(f"  Название: {description}")
            print(f"  Ссылка: {document_url}")
            content = fetch(document_url, args.timeout)
            if isinstance(content, str):
                content = content.encode("utf-8")
            saved_path = save_api_document(company, publication_date, filename, document_url, content, args.out)
            print(f"  Скачан: {saved_path}")
            try:
                print_market_window(company.ticker, publication_date, args.timeout)
            except (urllib.error.URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as exc:
                print(f"  Не удалось получить котировки MOEX: {exc}")
            if args.download_rsbu and company.code == "pao_rosseti_volga":
                try:
                    download_rsbu_q3(args.rsbu_year or args.year, args.out, args.timeout)
                except (urllib.error.URLError, TimeoutError, OSError, RuntimeError, ValueError) as exc:
                    print(f"  Не удалось скачать отчёт РСБУ: {exc}")
            extract_and_analyze(saved_path, args.out, args.analyze, args.print_excel, args.list_sheets)
            print()
            found += 1
        except (urllib.error.URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError, zipfile.BadZipFile, RuntimeError) as exc:
            print(f"  Ошибка: {exc}\n")
    print(f"Найдено приказов: {found}/{len(companies)}")
    return 0 if found else 3


if __name__ == "__main__":
    raise SystemExit(main())
