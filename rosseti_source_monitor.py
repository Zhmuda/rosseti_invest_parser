#!/usr/bin/env python3
"""Monitor Rosseti disclosure sources and send new documents to Telegram."""

from __future__ import annotations

import argparse
import html
import io
import json
import logging
import logging.handlers
import os
import re
import sqlite3
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zipfile
from datetime import date, datetime
from html.parser import HTMLParser
from pathlib import Path
from zoneinfo import ZoneInfo

try:
    import certifi
except ImportError:
    certifi = None


def load_local_env() -> None:
    """Load local .env without overriding Docker or shell environment."""
    env_path = Path(".env")
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key.strip(), value)


load_local_env()

from parse_rosseti_ipr_orders import ApiCompany, SITE, api_companies, api_get, api_order, fetch, moex_history


RSBU_URL = (
    "https://www.rossetivolga.ru/ru/aktsioneram_i_investoram/"
    "raskritie_informatsii_obcshestvom_i_otchetnaya_informatsiya/"
    "finansovaya_%28buhgalterskaya%29_otchetnost_po_rsbu"
)
RSBU_CODE = "pao_rosseti_volga"
COMPANY_NAME = "ПАО «Россети Волга»"
CENTER_RSBU_PAGE = "https://www.mrsk-1.ru/information/statements/rsbu/{year}/"
CENTER_COMPANY_NAME = "ПАО «Россети Центр»"
CENTER_CODE = "pao_rosseti_tsentr"
MR_RSBU_PAGE = "https://rossetimr.ru/invest_news/otchetnost/otchet_rsby/"
MR_COMPANY_NAME = "ПАО «Россети Московский регион»"
MR_EDISCLOSURE_PAGE = "https://www.e-disclosure.ru/portal/files.aspx?id=5563&type=3"
MR_EDISCLOSURE_PAGES = (
    MR_EDISCLOSURE_PAGE,
    "https://e-disclosure.ru/portal/files.aspx?id=5563&type=3",
)
SZ_RSBU_PAGE = "https://www.rosseti-sz.ru/investors/1yearfinreport/"
SZ_COMPANY_NAME = "ПАО «Россети Северо-Запад»"
SZ_CODE = "pao_rosseti_severo_zapad_ranee_pao_mrsk_severo_zapada_"
LSNG_RSBU_PAGE = "https://rosseti-lenenergo.ru/shareholders/fin_reports/"
LSNG_COMPANY_NAME = "ПАО «Россети Ленэнерго»"
LSNG_CODE = "pao_rosseti_lenenergo"
YUG_RSBU_PAGES = (
    "https://rosseti-yug.ru/aktsioneru-investoru/{year}-god/",
    "https://rosseti-yug.ru/aktsioneru-investoru/{year}-god_11/",
)
YUG_COMPANY_NAME = "ПАО «Россети Юг»"
YUG_CODE = "pao_rosseti_yug"
SOURCE_TICKERS = {
    "rsbu": "MRKV", "ipr": "MRKV",
    "rsbu_center": "MRKC", "ipr_center": "MRKC",
    "rsbu_sz": "MRKZ", "ipr_sz": "MRKZ",
    "rsbu_lsng": "LSNG", "ipr_lsng": "LSNG",
    "rsbu_yug": "MRKY", "ipr_yug": "MRKY",
}
COMPANY_NAMES = {
    "volga": COMPANY_NAME,
    "center": CENTER_COMPANY_NAME,
    "sz": SZ_COMPANY_NAME,
    "lsng": LSNG_COMPANY_NAME,
    "yug": YUG_COMPANY_NAME,
}
COMPANY_SOURCES = {
    "volga": ("rsbu", "ipr"),
    "center": ("rsbu_center", "ipr_center"),
    "sz": ("rsbu_sz", "ipr_sz"),
    "lsng": ("rsbu_lsng", "ipr_lsng"),
    "yug": ("rsbu_yug", "ipr_yug"),
}
COMPANY_ALIASES = {
    "волга": "volga", "mrkv": "volga",
    "центр": "center", "цент": "center", "mrkc": "center",
    "сз": "sz", "северо-запад": "sz", "северозапад": "sz", "mrkz": "sz",
    "ленэнерго": "lsng", "лен": "lsng", "lsng": "lsng",
    "юг": "yug", "mrky": "yug",
}
MSK = ZoneInfo("Europe/Moscow")
USER_AGENT = "Energo-Rosseti-Source-Monitor/1.0"
BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where() if certifi else None)
DIRECT_OPENER = urllib.request.build_opener(
    urllib.request.ProxyHandler({}),
    urllib.request.HTTPSHandler(context=SSL_CONTEXT),
)
INSECURE_DIRECT_OPENER = urllib.request.build_opener(
    urllib.request.ProxyHandler({}),
    urllib.request.HTTPSHandler(context=ssl._create_unverified_context()),
)


def open_url(req: urllib.request.Request, timeout: int):
    try:
        return DIRECT_OPENER.open(req, timeout=timeout)
    except urllib.error.URLError as direct_error:
        if not isinstance(direct_error.reason, ssl.SSLCertVerificationError):
            raise
        logging.warning("SSL-сертификат %s не прошёл проверку; повторяю прямой запрос без проверки сертификата", req.full_url)
        return INSECURE_DIRECT_OPENER.open(req, timeout=timeout)


def normalized_request_url(url: str) -> str:
    """Quote spaces and non-ASCII characters in a discovered URL path."""
    parts = urllib.parse.urlsplit(url)
    path = urllib.parse.quote(parts.path, safe="/%:@-._~!$&'()*+,;=%")
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, path, parts.query, parts.fragment))


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []
        self._depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            if self._href is not None:
                self._depth += 1
            return
        if self._href is not None:
            self._depth += 1
            return
        attributes = dict(attrs)
        self._href = html.unescape(attributes.get("href") or "")
        self._text = []
        self._depth = 0

    def handle_endtag(self, tag: str) -> None:
        if self._href is None:
            return
        if tag.lower() == "a" and self._depth == 0:
            self.links.append((self._href, " ".join("".join(self._text).split())))
            self._href = None
            self._text = []
            return
        if self._depth:
            self._depth -= 1

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text.append(data)


def normalized(value: str) -> str:
    value = html.unescape(value).replace("\xa0", " ")
    return re.sub(r"\s+", " ", value).strip()


def request(url: str, timeout: int = 60) -> bytes:
    url = normalized_request_url(url)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    with open_url(req, timeout) as response:
        return response.read()


def request_browser(url: str, timeout: int = 60) -> bytes:
    url = normalized_request_url(url)
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": BROWSER_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.e-disclosure.ru/",
            "Upgrade-Insecure-Requests": "1",
        },
    )
    with open_url(req, timeout) as response:
        return response.read()


def request_post(url: str, data: dict[str, str], timeout: int = 60) -> bytes:
    body = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "*/*",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
        },
        method="POST",
    )
    with open_url(req, timeout) as response:
        return response.read()


def request_page_and_ajax(url: str, data: dict[str, str], timeout: int = 60) -> tuple[bytes, bytes]:
    """Load a page and its AJAX tab using the same cookies/session."""
    cookies = urllib.request.HTTPCookieProcessor()
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}),
        cookies,
        urllib.request.HTTPSHandler(context=SSL_CONTEXT),
    )
    get_request = urllib.request.Request(
        url,
        headers={
            "User-Agent": BROWSER_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        },
    )
    with opener.open(get_request, timeout=timeout) as response:
        page = response.read()

    body = urllib.parse.urlencode(data).encode("utf-8")
    post_request = urllib.request.Request(
        url,
        data=body,
        headers={
            "User-Agent": BROWSER_USER_AGENT,
            "Accept": "text/html, */*; q=0.01",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": url,
            "Origin": "https://rossetimr.ru",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        },
        method="POST",
    )
    with opener.open(post_request, timeout=timeout) as response:
        ajax_page = response.read()
    return page, ajax_page


def extract_ipr_excels(content: bytes, output: Path, year: int, company_name: str) -> list[Path]:
    """Extract only Excel members from a Minenergo ZIP archive."""
    output.mkdir(parents=True, exist_ok=True)
    extracted: list[Path] = []
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        for info in archive.infolist():
            if not info.filename.lower().endswith((".xlsx", ".xlsm")):
                continue
            safe_company = re.sub(r"[^\wА-Яа-яЁё.-]+", "_", company_name).strip("_")
            target = output / f"{safe_company}_ИПР_{year}_{Path(info.filename).name}"
            target.write_bytes(archive.read(info))
            extracted.append(target)
    if not extracted:
        raise RuntimeError("В ZIP Минэнерго не найден Excel-файл")
    return extracted


def cleanup_files(paths: list[str], output: Path, source: str) -> None:
    """Remove files owned by this monitor for one source only."""
    candidates = {Path(item) for item in paths}
    candidates.update(output.glob("*"))
    for path in candidates:
        try:
            if path.is_file():
                path.unlink()
                logging.info("Удалён файл %s", path)
        except OSError:
            logging.exception("Не удалось удалить файл %s", path)


def publication_date_from_url(url: str) -> str | None:
    match = re.search(r"/i/files/(\d{4})/(\d{1,2})/(\d{1,2})/", url)
    if not match:
        return None
    year, month, day = (int(value) for value in match.groups())
    try:
        return date(year, month, day).strftime("%d.%m.%Y")
    except ValueError:
        return None


def find_rsbu_report(year: int, timeout: int) -> tuple[str, str, str]:
    page = request(RSBU_URL, timeout).decode("utf-8", errors="replace")
    parser = LinkParser()
    parser.feed(page)
    title_re = re.compile(
        rf"бухгалтерская\s+отчетность\s+за\s*3\s*квартал\s*{year}\s*года", re.I
    )
    for href, text in parser.links:
        title = normalized(text)
        if title_re.search(title):
            url = urllib.parse.urljoin(RSBU_URL, href)
            publication = publication_date_from_url(url) or "не указана"
            return title, url, publication
    raise RuntimeError(f"РСБУ за 3 квартал {year} года не найден")


def find_center_rsbu_report(year: int, timeout: int) -> tuple[str, str, str]:
    """Find Rosseti Centre's RAS report for nine months of the year."""
    page_url = CENTER_RSBU_PAGE.format(year=year)
    page = request(page_url, timeout).decode("utf-8", errors="replace")
    parser = LinkParser()
    parser.feed(page)
    wanted_href = re.compile(rf"rsbu_9m_{year}\.pdf(?:$|[?#])", re.I)
    wanted_text = re.compile(rf"(?:30\.09\.{year}|9\s*мес\.?\s*{year})", re.I)
    for href, text in parser.links:
        url = urllib.parse.urljoin(page_url, href)
        if wanted_href.search(url) or wanted_text.search(normalized(text)):
            publication = "не указана"
            position = page.find(href)
            if position >= 0:
                window = page[max(0, position - 2500):position + 1500]
                dates = re.findall(r"\b(\d{2}\.\d{2}\.\d{4})\b", window)
                if dates:
                    publication = dates[0]
            return f"Бухгалтерская отчетность на 30.09.{year}", url, publication
    raise RuntimeError(f"РСБУ «Россети Центр» за 9 месяцев {year} года не найден")


def find_mr_rsbu_report(year: int, timeout: int) -> tuple[str, str, str]:
    """Find Rosseti Moscow Region's RAS report for nine months of the year."""
    base_page_bytes, _ = request_page_and_ajax(MR_RSBU_PAGE, {"tab": f"tab15-{year}"}, timeout)
    base_page = base_page_bytes.decode("utf-8", errors="replace")
    ajax_pages: list[str] = []
    tab_values = (
        f"tab15-{year}",
        f"15-{year}",
        f"tab-15-{year}",
        f"15_{year}",
        str(year),
        "15",
    )
    for tab_value in tab_values:
        try:
            _, ajax_page_bytes = request_page_and_ajax(MR_RSBU_PAGE, {"tab": tab_value}, timeout)
            ajax_page_text = ajax_page_bytes.decode("utf-8", errors="replace")
            ajax_pages.append(ajax_page_text)
            if logging.getLogger().isEnabledFor(logging.DEBUG):
                debug_tab_path = Path("data/rosseti_ipr_orders") / f"debug_rossetimr_rsbu_{year}_{tab_value.replace('-', '_')}.html"
                debug_tab_path.write_text(ajax_page_text, encoding="utf-8")
            logging.debug("Россети Московский регион: AJAX tab=%s, размер ответа=%s", tab_value, len(ajax_page_bytes))
        except Exception:
            logging.debug("Не удалось получить AJAX tab=%s", tab_value, exc_info=True)
    ajax_page = "\n".join(ajax_pages)
    page = ajax_page + "\n" + base_page
    if logging.getLogger().isEnabledFor(logging.DEBUG):
        debug_path = Path("data/rosseti_ipr_orders") / f"debug_rossetimr_rsbu_{year}.html"
        debug_path.parent.mkdir(parents=True, exist_ok=True)
        debug_path.write_text(page, encoding="utf-8")
        logging.debug("Ответы страницы сохранены в %s (%s знаков; AJAX: %s)", debug_path, len(page), len(ajax_page))
    parser = LinkParser()
    parser.feed(page)
    wanted_text = re.compile(
        rf"бухгалтерская\s*\(финансовая\)\s*отчетность\s+за\s*9\s*месяцев\s*{year}\s*года",
        re.I,
    )
    wanted_href = re.compile(rf"9[^\"']*месяц[^\"']*{year}[^\"']*\.pdf", re.I)
    for href, text in parser.links:
        url = urllib.parse.urljoin(MR_RSBU_PAGE, href)
        searchable = normalized(f"{text} {urllib.parse.unquote(url)}")
        if not (wanted_text.search(searchable) or wanted_href.search(urllib.parse.unquote(url))):
            continue
        publication = "не указана"
        position = page.find(href)
        if position >= 0:
            window = page[max(0, position - 2500):position + 1500]
            dates = re.findall(r"\b(\d{2}\.\d{2}\.\d{4})\b", window)
            if dates:
                publication = dates[0]
        return f"Бухгалтерская (финансовая) отчетность за 9 месяцев {year} года", url, publication

    # Резервный разбор атрибутов href/data-href, если ссылка находится внутри
    # нестандартной разметки вкладки и HTMLParser не собрал её как <a>.
    raw_link_re = re.compile(r"(?:href|data-href)\s*=\s*[\"']([^\"']+\.pdf(?:\?[^\"']*)?)[\"']", re.I)
    for raw_href in raw_link_re.findall(page):
        url = urllib.parse.urljoin(MR_RSBU_PAGE, html.unescape(raw_href))
        decoded_url = urllib.parse.unquote(url)
        if re.search(rf"9\s*месяцев\s*{year}[^/]*\.pdf", decoded_url, re.I):
            return f"Бухгалтерская (финансовая) отчетность за 9 месяцев {year} года", url, "не указана"

    # Некоторые вкладки сайта формируются нестандартной разметкой или JS,
    # поэтому ищем также любые PDF-строки во всём исходном HTML.
    raw_pdf_re = re.compile(r"[\"']([^\"']+\.pdf(?:\?[^\"']*)?)[\"']", re.I)
    for raw_href in raw_pdf_re.findall(page):
        decoded_url = urllib.parse.unquote(html.unescape(raw_href))
        if re.search(rf"9\s*месяцев\s*{year}[^/]*\.pdf", decoded_url, re.I):
            url = urllib.parse.urljoin(MR_RSBU_PAGE, html.unescape(raw_href))
            return f"Бухгалтерская (финансовая) отчетность за 9 месяцев {year} года", url, "не указана"

    # Ещё один вариант: URL может быть без кавычек в JSON/JS-объекте или
    # содержать экранированные слэши.
    page_for_search = html.unescape(page).replace("\\/", "/")
    loose_pdf_re = re.compile(r"(?:(?:https?:)?//|/)[^<>'\"\s]+\.pdf(?:\?[^<>'\"\s]*)?", re.I)
    loose_candidates = loose_pdf_re.findall(page_for_search)
    logging.debug("%s: найдено PDF-кандидатов в HTML: %s", MR_RSBU_PAGE, len(loose_candidates))
    for raw_href in loose_candidates:
        decoded_href = urllib.parse.unquote(raw_href)
        if re.search(rf"9\s*месяцев\s*{year}[^/]*\.pdf", decoded_href, re.I):
            url = urllib.parse.urljoin(MR_RSBU_PAGE, raw_href)
            return f"Бухгалтерская (финансовая) отчетность за 9 месяцев {year} года", url, "не указана"

    raise RuntimeError(f"РСБУ «Россети Московский регион» за 9 месяцев {year} года не найден")


def find_mr_edisclosure_report(year: int, timeout: int) -> tuple[str, str, str]:
    """Find MR's interim RAS archive in the e-disclosure file register."""
    page = None
    page_url = MR_EDISCLOSURE_PAGE
    for candidate_url in MR_EDISCLOSURE_PAGES:
        try:
            page = request_browser(candidate_url, timeout).decode("utf-8", errors="replace")
            page_url = candidate_url
            break
        except urllib.error.HTTPError as exc:
            if exc.code != 403:
                raise
    if page is None:
        raise RuntimeError("e-disclosure заблокировал доступ к реестру (HTTP 403)")
    if logging.getLogger().isEnabledFor(logging.DEBUG):
        debug_path = Path("data/rosseti_ipr_orders") / f"debug_edisclosure_mr_{year}.html"
        debug_path.parent.mkdir(parents=True, exist_ok=True)
        debug_path.write_text(page, encoding="utf-8")
        logging.debug("Ответ e-disclosure сохранён в %s (%s знаков)", debug_path, len(page))
    parser = LinkParser()
    parser.feed(page)
    title_re = re.compile(r"промежуточн\w*\s+бухгалтерск\w*\s+отчетност\w*", re.I)
    period_re = re.compile(r"(?:9\s*месяц\w*|январ\w*\s*[-–—]\s*сентябр\w*)", re.I)
    year_re = re.compile(rf"\b{year}\b")
    for href, text in parser.links:
        url = urllib.parse.urljoin(page_url, href)
        position = page.find(href)
        nearby = page[max(0, position - 3500):position + 2000] if position >= 0 else ""
        searchable = normalized(f"{text} {nearby}")
        if title_re.search(searchable) and period_re.search(searchable) and year_re.search(searchable):
            dates = re.findall(r"\b(\d{2}\.\d{2}\.\d{4})\b", nearby)
            return (
                f"Промежуточная бухгалтерская отчетность (все формы), {year}, 9 месяцев",
                url,
                dates[0] if dates else "не указана",
            )
    raise RuntimeError(f"РСБУ «Россети Московский регион» за 9 месяцев {year} года в e-disclosure не найден")


def find_sz_rsbu_report(year: int, timeout: int) -> tuple[str, str, str]:
    """Find Rosseti North-West's RAS report for nine months of the year."""
    page = request(SZ_RSBU_PAGE, timeout).decode("utf-8", errors="replace")
    parser = LinkParser()
    parser.feed(page)
    wanted = re.compile(rf"9\s*месяцев[^\d]{{0,30}}{year}", re.I)
    latin_filename = re.compile(rf"9[-_ ]*mesyatsev[-_ ]*{year}", re.I)
    for href, text in parser.links:
        url = urllib.parse.urljoin(SZ_RSBU_PAGE, href)
        decoded_url = urllib.parse.unquote(url)
        searchable = normalized(f"{text} {decoded_url}")
        if not decoded_url.lower().split("?", 1)[0].endswith(".pdf"):
            continue
        position = page.find(href)
        nearby = page[max(0, position - 2500):position + 1500] if position >= 0 else ""
        if wanted.search(searchable) or wanted.search(normalized(nearby)) or latin_filename.search(decoded_url):
            return f"Бухгалтерская (финансовая) отчетность за 9 месяцев {year} года", url, "не указана"

    # Резервный разбор URL в нестандартной HTML-разметке.
    raw_pdf_re = re.compile(r"[\"']([^\"']+\.pdf(?:\?[^\"']*)?)[\"']", re.I)
    for raw_href in raw_pdf_re.findall(page):
        url = urllib.parse.urljoin(SZ_RSBU_PAGE, html.unescape(raw_href))
        decoded_url = urllib.parse.unquote(url)
        if latin_filename.search(decoded_url):
            return f"Бухгалтерская (финансовая) отчетность за 9 месяцев {year} года", url, "не указана"
    raise RuntimeError(f"РСБУ «Россети Северо-Запад» за 9 месяцев {year} года не найден")


def find_lsng_rsbu_report(year: int, timeout: int) -> tuple[str, str, str]:
    """Find Rosseti Lenenergo's RAS report for January-September."""
    page = request(LSNG_RSBU_PAGE, timeout).decode("utf-8", errors="replace")
    parser = LinkParser()
    parser.feed(page)
    period_re = re.compile(rf"(?:январ\w*\s*[-–—]\s*сентябр\w*|9\s*месяц\w*)[^\d]{{0,30}}{year}", re.I)
    filename_re = re.compile(rf"(?:9|январ)[^/]*{year}[^/]*\.pdf", re.I)
    for href, text in parser.links:
        url = urllib.parse.urljoin(LSNG_RSBU_PAGE, href)
        decoded_url = urllib.parse.unquote(url)
        if not decoded_url.lower().split("?", 1)[0].endswith(".pdf"):
            continue
        position = page.find(href)
        nearby = page[max(0, position - 2500):position + 1500] if position >= 0 else ""
        searchable = normalized(f"{text} {decoded_url}")
        if period_re.search(searchable) or period_re.search(normalized(nearby)) or filename_re.search(decoded_url):
            return f"Бухгалтерская отчетность за январь - сентябрь {year} года", url, "не указана"
    raise RuntimeError(f"РСБУ «Россети Ленэнерго» за январь - сентябрь {year} года не найден")


def find_yug_rsbu_report(year: int, timeout: int) -> tuple[str, str, str]:
    """Find Rosseti South's RAS report for January-September."""
    pages: list[tuple[str, str]] = []
    for page_template in YUG_RSBU_PAGES:
        page_url = page_template.format(year=year)
        try:
            page = request(page_url, timeout).decode("utf-8", errors="replace")
        except urllib.error.URLError:
            continue
        pages.append((page_url, page))

    period_re = re.compile(
        rf"(?:январ\w*\s*[-–—]\s*сентябр\w*|9\s*месяц\w*)[^\d]{{0,40}}{year}", re.I
    )
    accounting_re = re.compile(
        r"(?:бухгалтерск\w*\s*(?:\(\s*финансов\w*\s*\))?\s*отчетност\w*|"
        r"финансов\w*\s*отчетност\w*|рсбу)",
        re.I,
    )
    filename_re = re.compile(rf"(?:9|yanvar|сентябр)[^/]*{year}[^/]*\.pdf", re.I)
    for page_url, page in pages:
        parser = LinkParser()
        parser.feed(page)
        for href, text in parser.links:
            url = urllib.parse.urljoin(page_url, href)
            decoded_url = urllib.parse.unquote(url)
            if not decoded_url.lower().split("?", 1)[0].endswith(".pdf"):
                continue
            position = page.find(href)
            nearby = page[max(0, position - 2500):position + 1500] if position >= 0 else ""
            searchable = normalized(f"{text} {decoded_url}")
            context = normalized(f"{searchable} {nearby}")
            if re.search(r"(?:мсфо|ifrs|консолидирован)", context, re.I):
                continue
            if accounting_re.search(context) and (
                period_re.search(context) or filename_re.search(decoded_url)
            ):
                return f"Бухгалтерская (финансовая) отчетность за январь - сентябрь {year} года", url, "не указана"

        raw_pdf_re = re.compile(r"[\"']([^\"']+\.pdf(?:\?[^\"']*)?)[\"']", re.I)
        for raw_href in raw_pdf_re.findall(page):
            url = urllib.parse.urljoin(page_url, html.unescape(raw_href))
            decoded_url = urllib.parse.unquote(url)
            position = page.find(raw_href)
            nearby = page[max(0, position - 2500):position + 1500] if position >= 0 else ""
            context = normalized(f"{decoded_url} {nearby}")
            if (
                not re.search(r"(?:мсфо|ifrs|консолидирован)", context, re.I)
                and accounting_re.search(context)
                and (period_re.search(context) or filename_re.search(decoded_url))
            ):
                return f"Бухгалтерская (финансовая) отчетность за январь - сентябрь {year} года", url, "не указана"
    raise RuntimeError(f"РСБУ «Россети Юг» за январь - сентябрь {year} года не найден")


def find_ipr_report(year: int, timeout: int, company_code: str, company_name: str) -> tuple[str, str, str]:
    company = next((item for item in api_companies(timeout) if item.code == company_code), None)
    if company is None:
        raise RuntimeError(f"{company_name} не найдено в API Минэнерго")
    payload = api_get("organizations.getItemDetail", timeout, code=company.code)
    result = api_order(company, payload, year)
    if result is None:
        raise RuntimeError(f"Приказ Минэнерго для {company_name} за {year} год не найден")
    title, publication, url, _filename = result
    return title, url, publication


def market_summary(source: str, publication: str, timeout: int) -> str:
    ticker = SOURCE_TICKERS.get(source)
    if not ticker:
        return "Котировки MOEX: тикер для источника не настроен"
    current_price = None
    try:
        url = f"https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities/{ticker}.json?iss.meta=off"
        payload = fetch(url, timeout)
        if isinstance(payload, bytes):
            payload = payload.decode("utf-8", errors="replace")
        marketdata = json.loads(payload).get("marketdata", {})
        columns = marketdata.get("columns", [])
        rows = [dict(zip(columns, row)) for row in marketdata.get("data", [])]
        if rows:
            current_price = rows[0].get("LAST") or rows[0].get("MARKETPRICE")
    except Exception:
        logging.exception("Не удалось получить текущую котировку MOEX для %s", ticker)

    result = [f"Котировки MOEX ({ticker}, TQBR):"]
    if current_price is not None:
        result.append(f"  текущая цена: {current_price}")
    else:
        result.append("  текущая цена: не получена")

    date_match = re.search(r"^(\d{2})\.(\d{2})\.(\d{4})$", publication or "")
    if not date_match:
        result.append("  цена за день до публикации: дата публикации не распознана")
        return "\n".join(result)
    publication_date = date(int(date_match.group(3)), int(date_match.group(2)), int(date_match.group(1)))
    try:
        rows = moex_history(ticker, publication_date, timeout)
        previous = [row for row in rows if row.get("TRADEDATE", "") < publication_date.isoformat()]
        if previous:
            row = previous[-1]
            close = row.get("CLOSE") or row.get("LEGALCLOSEPRICE")
            result.append(f"  день до публикации ({row.get('TRADEDATE')}): закрытие={close}")
        else:
            result.append("  цена за день до публикации: данных нет")
    except Exception:
        logging.exception("Не удалось получить историю MOEX для %s", ticker)
        result.append("  цена за день до публикации: данные не получены")
    return "\n".join(result)


def setup_logging(debug: bool) -> None:
    log_path = Path("data/rosseti_ipr_orders/rosseti_source_monitor.log")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    level = logging.DEBUG if debug else getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    file_handler = logging.handlers.RotatingFileHandler(
        log_path, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)
    root.addHandler(file_handler)
    root.addHandler(console_handler)


class State:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.execute("CREATE TABLE IF NOT EXISTS source_state (source TEXT PRIMARY KEY, data TEXT NOT NULL)")
        self.db.commit()

    def get(self, source: str, default: dict) -> dict:
        row = self.db.execute("SELECT data FROM source_state WHERE source = ?", (source,)).fetchone()
        return json.loads(row[0]) if row else default.copy()

    def put(self, source: str, data: dict) -> None:
        self.db.execute(
            "INSERT INTO source_state(source, data) VALUES(?, ?) "
            "ON CONFLICT(source) DO UPDATE SET data=excluded.data",
            (source, json.dumps(data, ensure_ascii=False)),
        )
        self.db.commit()


class Telegram:
    def __init__(self, token: str, chat_id: str) -> None:
        if not token or not chat_id:
            raise RuntimeError("нужны ROSSETI_TELEGRAM_BOT_TOKEN/TELEGRAM_BOT_TOKEN и chat_id")
        self.base = f"https://api.telegram.org/bot{token}/"
        self.chat_id = chat_id

    def call(self, method: str, payload: dict) -> dict:
        body = urllib.parse.urlencode(payload).encode()
        req = urllib.request.Request(self.base + method, data=body, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read())
        if not result.get("ok"):
            raise RuntimeError(f"Telegram {method}: {result}")
        return result

    def send_message(self, text: str, source: str) -> None:
        self.call("sendMessage", {
            "chat_id": self.chat_id,
            "text": text,
            "reply_markup": json.dumps({"inline_keyboard": [[{
                "text": "Прекратить анализ этого источника",
                "callback_data": f"stop:{source}",
            }]]}, ensure_ascii=False),
        })

    def send_status_message(self, text: str, force_reply: bool = False) -> dict:
        payload = {
            "chat_id": self.chat_id,
            "text": text,
        }
        if force_reply:
            payload["reply_markup"] = json.dumps({"force_reply": True, "selective": True})
        return self.call("sendMessage", payload)

    def send_document(self, path: Path) -> None:
        boundary = "----Energo" + uuid.uuid4().hex
        chunks: list[bytes] = []

        def field(name: str, value: str) -> None:
            chunks.extend([
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
                value.encode(), b"\r\n",
            ])

        field("chat_id", self.chat_id)
        chunks.extend([
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="document"; filename="{path.name}"\r\n'.encode(),
            b"Content-Type: application/octet-stream\r\n\r\n",
            path.read_bytes(), b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ])
        req = urllib.request.Request(
            self.base + "sendDocument",
            data=b"".join(chunks),
            headers={"User-Agent": USER_AGENT, "Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read())
        if not result.get("ok"):
            raise RuntimeError(f"Telegram sendDocument: {result}")

    def updates(self, offset: int) -> list[dict]:
        return self.call("getUpdates", {
            "offset": offset,
            "timeout": 1,
            "allowed_updates": json.dumps(["message", "callback_query"]),
        }).get("result", [])

    def answer(self, callback_id: str, text: str) -> None:
        self.call("answerCallbackQuery", {"callback_query_id": callback_id, "text": text})


def in_window(source: str, today: date) -> bool:
    if source in {"rsbu", "rsbu_center", "rsbu_sz", "rsbu_lsng", "rsbu_yug"}:
        return today.month == 10 and 10 <= today.day <= 31 or today.month == 11 and today.day <= 10
    return today.month == 12 and 10 <= today.day <= 31


def next_year_if_window_finished(source: str, state: dict, today: date) -> bool:
    target_year = int(state.get("target_year", today.year))
    if today.year < target_year:
        return False
    if today.year > target_year:
        state["target_year"] = today.year
        return state.get("status") == "waiting"
    if source in {"rsbu", "rsbu_center", "rsbu_sz", "rsbu_lsng", "rsbu_yug"}:
        finished = (today.month == 11 and today.day > 10) or today.month == 12
    else:
        finished = today.month == 12 and today.day > 31
    if finished and state.get("status") == "waiting":
        state["target_year"] += 1
        return True
    return False


def poll_source(source: str, target_year: int, timeout: int) -> tuple[str, str, str] | None:
    if source == "rsbu":
        return find_rsbu_report(target_year, timeout)
    if source == "rsbu_center":
        return find_center_rsbu_report(target_year, timeout)
    if source == "rsbu_sz":
        return find_sz_rsbu_report(target_year, timeout)
    if source == "rsbu_lsng":
        return find_lsng_rsbu_report(target_year, timeout)
    if source == "rsbu_yug":
        return find_yug_rsbu_report(target_year, timeout)
    if source == "ipr_center":
        return find_ipr_report(target_year, timeout, CENTER_CODE, CENTER_COMPANY_NAME)
    if source == "ipr_sz":
        return find_ipr_report(target_year, timeout, SZ_CODE, SZ_COMPANY_NAME)
    if source == "ipr_lsng":
        return find_ipr_report(target_year, timeout, LSNG_CODE, LSNG_COMPANY_NAME)
    if source == "ipr_yug":
        return find_ipr_report(target_year, timeout, YUG_CODE, YUG_COMPANY_NAME)
    return find_ipr_report(target_year, timeout, RSBU_CODE, COMPANY_NAME)


def company_key_for_source(source: str) -> str:
    for key, company_sources in COMPANY_SOURCES.items():
        if source in company_sources:
            return key
    return "volga"


def history_response(state: State, company_key: str) -> str:
    lines = [f"История анализа: {COMPANY_NAMES[company_key]}"]
    has_entries = False
    for source in COMPANY_SOURCES[company_key]:
        source_state = state.get(source, {"target_year": 2026, "status": "waiting"})
        entries = source_state.get("history", [])
        if not entries:
            continue
        has_entries = True
        lines.append(f"\n{source}:")
        for entry in entries:
            lines.append(f"{entry.get('created_at', 'дата не указана')}:\n{entry.get('text', '')}")
    if not has_entries:
        lines.append("\nСохранённых результатов пока нет.")
    return "\n".join(lines)[-3900:]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="проверить источники один раз")
    parser.add_argument("--source", choices=("rsbu", "rsbu_center", "rsbu_sz", "rsbu_lsng", "rsbu_yug", "ipr", "ipr_center", "ipr_sz", "ipr_lsng", "ipr_yug"), help="проверить только один источник")
    parser.add_argument("--download-only", action="store_true", help="скачать документ без отправки в Telegram и без сохранения состояния")
    parser.add_argument("--state", type=Path, default=Path("data/rosseti_source_monitor.sqlite3"))
    parser.add_argument("--out", type=Path, default=Path("data/rosseti_ipr_orders/monitor"))
    parser.add_argument("--poll-seconds", type=int, default=int(os.getenv("ROSSETI_POLL_SECONDS", "3600")))
    parser.add_argument("--year", type=int, default=int(os.getenv("ROSSETI_START_YEAR", "2026")))
    parser.add_argument("--debug", action="store_true", help="сохранить отладочные сообщения о найденных ссылках")
    args = parser.parse_args()
    setup_logging(args.debug)
    logging.info("Монитор запущен: проверка источников выполняется ежедневно с 07:00 до 00:00 по Москве")
    token = os.getenv("ROSSETI_TELEGRAM_BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("ROSSETI_TELEGRAM_CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID", "")
    telegram = None if args.download_only else Telegram(token, chat_id)
    state = State(args.state)
    sources = {
        "rsbu": "Бухгалтерская отчетность за 3 квартал",
        "rsbu_center": "Бухгалтерская отчетность «Россети Центр» за 9 месяцев",
        "rsbu_sz": "Бухгалтерская отчетность «Россети Северо-Запад» за 9 месяцев",
        "rsbu_lsng": "Бухгалтерская отчетность «Россети Ленэнерго» за 9 месяцев",
        "rsbu_yug": "Бухгалтерская отчетность «Россети Юг» за 9 месяцев",
        "ipr": "Приказ Минэнерго России по инвестиционной программе",
        "ipr_center": "Приказ Минэнерго России по инвестиционной программе «Россети Центр»",
        "ipr_sz": "Приказ Минэнерго России по инвестиционной программе «Россети Северо-Запад»",
        "ipr_lsng": "Приказ Минэнерго России по инвестиционной программе «Россети Ленэнерго»",
        "ipr_yug": "Приказ Минэнерго России по инвестиционной программе «Россети Юг»",
    }
    for source in sources:
        if not state.get(source, {"target_year": args.year, "status": "waiting"}).get("target_year"):
            state.put(source, {"target_year": args.year, "status": "waiting"})

    offset = 0
    next_source_check = 0.0
    while True:
        now = datetime.now(MSK)
        if time.monotonic() >= next_source_check and 7 <= now.hour < 24:
            today = now.date()
            for source in sources:
                if args.source and source != args.source:
                    continue
                if args.download_only:
                    # Тестовая загрузка не должна зависеть от сохранённого года
                    # и не должна менять рабочее состояние монитора.
                    source_state = {"target_year": args.year, "status": "waiting"}
                else:
                    source_state = state.get(source, {"target_year": args.year, "status": "waiting"})
                    if next_year_if_window_finished(source, source_state, today):
                        logging.info("%s: окно завершено, следующий год %s", source, source_state["target_year"])
                        state.put(source, source_state)
                if (not args.once and not in_window(source, today)) or source_state.get("status") != "waiting":
                    continue
                try:
                    result = poll_source(source, int(source_state["target_year"]), 60)
                    if result:
                        title, url, publication = result
                        was_error = bool(source_state.get("last_error"))
                        document = request(url, 120)
                        source_dir = args.out / source
                        company_name = (
                            CENTER_COMPANY_NAME if source in {"rsbu_center", "ipr_center"}
                            else SZ_COMPANY_NAME if source in {"rsbu_sz", "ipr_sz"}
                            else LSNG_COMPANY_NAME if source in {"rsbu_lsng", "ipr_lsng"}
                            else YUG_COMPANY_NAME if source in {"rsbu_yug", "ipr_yug"}
                            else COMPANY_NAME
                        )
                        safe_company = re.sub(r"[^\wА-Яа-яЁё.-]+", "_", company_name).strip("_")
                        if source in {"rsbu", "rsbu_center", "rsbu_sz", "rsbu_lsng", "rsbu_yug"}:
                            source_dir.mkdir(parents=True, exist_ok=True)
                            period = "3_квартал" if source == "rsbu" else "9_месяцев"
                            target = source_dir / f"{safe_company}_РСБУ_{period}_{source_state['target_year']}.pdf"
                            target.write_bytes(document)
                            files = [target]
                        else:
                            files = extract_ipr_excels(document, source_dir, int(source_state["target_year"]), company_name)
                        market = market_summary(source, publication, 60)
                        text = (
                            f"Компания: {company_name}\n"
                            f"Отчёт: {title}\n"
                            f"Дата публикации: {publication}\n"
                            f"Источник: {url}\n"
                            f"{market}"
                        )
                        if args.download_only:
                            logging.info("%s: документ скачан в %s", source, ", ".join(str(path) for path in files))
                            continue
                        if was_error:
                            telegram.send_message(
                                f"Источник восстановлен: {source}\n"
                                f"Компания: {company_name}\n"
                                f"Последняя ошибка больше не повторяется.",
                                source,
                            )
                        telegram.send_message(text, source)
                        for file_path in files:
                            telegram.send_document(file_path)
                        cleanup_files([str(path) for path in files], source_dir, source)
                        source_state.update({
                            "status": "notified", "url": url, "title": title,
                            "publication": publication, "files": [],
                            "last_error": "", "error_notified": False,
                        })
                        state.put(source, source_state)
                        logging.info("%s: новый документ отправлен в Telegram", source)
                except Exception as exc:
                    logging.exception("Ошибка проверки источника %s", source)
                    if not args.download_only and telegram is not None:
                        error_text = f"{type(exc).__name__}: {exc}"
                        if source_state.get("last_error") != error_text or not source_state.get("error_notified"):
                            company_name = (
                                CENTER_COMPANY_NAME if source in {"rsbu_center", "ipr_center"}
                                else SZ_COMPANY_NAME if source in {"rsbu_sz", "ipr_sz"}
                                else LSNG_COMPANY_NAME if source in {"rsbu_lsng", "ipr_lsng"}
                                else YUG_COMPANY_NAME if source in {"rsbu_yug", "ipr_yug"}
                                else COMPANY_NAME
                            )
                            alert = (
                                f"Ошибка источника\n"
                                f"Компания: {company_name}\n"
                                f"Источник: {source}\n"
                                f"Год: {source_state.get('target_year')}\n"
                                f"Ошибка: {error_text}\n"
                                f"Проверка будет повторена по расписанию."
                            )
                            try:
                                telegram.send_message(alert, source)
                                source_state["last_error"] = error_text
                                source_state["error_notified"] = True
                                state.put(source, source_state)
                            except Exception:
                                logging.exception("Не удалось отправить Telegram-уведомление об ошибке %s", source)
            next_source_check = time.monotonic() + max(60, args.poll_seconds)

        if args.download_only:
            return 0

        try:
            for update in telegram.updates(offset):
                offset = max(offset, int(update["update_id"]) + 1)
                message = update.get("message") or {}
                message_text = (message.get("text") or "").strip()
                command = message_text.split()[0].lower() if message_text else ""
                if command in {"/start", "/help"}:
                    telegram.send_status_message(
                        "Монитор источников Россетей работает.\n\n"
                        "РСБУ проверяется с 10 октября по 10 ноября.\n"
                        "Приказы Минэнерго проверяются с 10 по 31 декабря.\n\n"
                        "Проверка выполняется ежечасно с 07:00 до 00:00 по Москве.\n"
                        "После нахождения документа он отправляется сюда, а источник автоматически переводится в ожидание следующего года.\n\n"
                        "Команды истории: /history volga, /history center, /history sz, /history lsng, /history yug."
                    )
                    continue
                if command in {"/history", "/история"}:
                    parts = message_text.split(maxsplit=1)
                    requested = parts[1].strip().lower() if len(parts) > 1 else ""
                    if requested in {"all", "все"}:
                        response = "\n\n".join(history_response(state, key) for key in COMPANY_NAMES)
                    else:
                        company_key = COMPANY_ALIASES.get(requested, requested)
                        response = (
                            history_response(state, company_key)
                            if company_key in COMPANY_NAMES
                            else "Укажите компанию: volga, center, sz, lsng или yug."
                        )
                    telegram.send_status_message(response[-3900:])
                    continue
                reply_to = message.get("reply_to_message") or {}
                if message_text and reply_to.get("message_id"):
                    saved = False
                    for source in sources:
                        source_state = state.get(source, {"target_year": args.year, "status": "waiting"})
                        if source_state.get("history_prompt_id") != reply_to.get("message_id"):
                            continue
                        source_state.setdefault("history", []).append({
                            "created_at": datetime.now(MSK).strftime("%Y-%m-%d %H:%M:%S"),
                            "text": message_text,
                        })
                        source_state.pop("history_prompt_id", None)
                        state.put(source, source_state)
                        telegram.send_status_message(
                            f"Результаты анализа сохранены: {COMPANY_NAMES[company_key_for_source(source)]}."
                        )
                        saved = True
                        break
                    if saved:
                        continue
                callback = update.get("callback_query") or {}
                data = callback.get("data", "")
                if not data.startswith("stop:"):
                    continue
                source = data.split(":", 1)[1]
                if source not in sources:
                    continue
                source_state = state.get(source, {"target_year": args.year, "status": "waiting"})
                cleanup_files(source_state.get("files", []), args.out / source, source)
                source_state["status"] = "waiting"
                source_state["target_year"] = int(source_state.get("target_year", args.year)) + 1
                source_state["files"] = []
                prompt = telegram.send_status_message(
                    f"Анализ источника остановлен для {COMPANY_NAMES[company_key_for_source(source)]}.\n"
                    f"Следующая проверка запланирована на {source_state['target_year']} год.\n\n"
                    "Ответьте на это сообщение текстом с результатами анализа — я сохраню их в историю.",
                    force_reply=True,
                )
                source_state["history_prompt_id"] = prompt.get("result", {}).get("message_id")
                state.put(source, source_state)
                telegram.answer(callback["id"], "Источник остановлен. Следующая проверка запланирована на следующий год.")
                logging.info("%s: остановлен кнопкой, следующий год %s", source, source_state["target_year"])
        except Exception:
            logging.exception("Ошибка обработки Telegram callback")
        if args.once:
            return 0
        time.sleep(5)


if __name__ == "__main__":
    raise SystemExit(main())
