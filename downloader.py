import logging
import os
import re
import time
import tempfile
import zipfile
import hashlib
from html.parser import HTMLParser
from urllib.parse import urlencode, urljoin, urlparse
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from http.client import RemoteDisconnected


LOGGER = logging.getLogger(__name__)

WMS_URL = "https://mapy.geoportal.gov.pl/wss/service/PZGIK/BDOT/WMS/PobieranieBDOT10k"
WMS_QUERY_LAYER = "Powiaty"

HTTP_TIMEOUT = 90
HTTP_RETRIES = 4
RETRY_DELAYS = (1.0, 2.0, 4.0, 8.0)


class _LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self._href = None
        self._text = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a":
            self._href = dict(attrs).get("href")
            self._text = []

    def handle_data(self, data):
        if self._href:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self._href:
            self.links.append(
                (self._href, " ".join(self._text).strip())
            )
            self._href = None
            self._text = []


def _validate_geoportal_url(url):
    """Accept only HTTPS URLs hosted by Geoportal domains."""
    parsed = urlparse(str(url))
    hostname = (parsed.hostname or "").lower()
    if parsed.scheme.lower() != "https":
        raise ValueError(f"Unsupported URL scheme: {parsed.scheme or '<none>'}")
    if hostname != "geoportal.gov.pl" and not hostname.endswith(".geoportal.gov.pl"):
        raise ValueError(f"Unsupported download host: {hostname or '<none>'}")
    return parsed.geturl()


def _request(url):
    url = _validate_geoportal_url(url)
    return Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 QuickBDOT/0.0.38",
            "Accept": "*/*",
            "Accept-Encoding": "identity",
            "Connection": "close",
        },
    )


def _open_with_retry(url, timeout=HTTP_TIMEOUT):
    """
    Otwiera URL z ponawianiem połączenia.
    Geoportal przy serii szybkich zapytań potrafi zamknąć połączenie.
    """
    last_error = None

    for attempt in range(HTTP_RETRIES):
        try:
            return urlopen(  # nosec B310 - URL is validated as HTTPS Geoportal
                _request(url),
                timeout=timeout,
            )

        except (
            RemoteDisconnected,
            ConnectionResetError,
            TimeoutError,
            URLError,
            HTTPError,
            OSError,
        ) as error:
            last_error = error

            if attempt >= HTTP_RETRIES - 1:
                break

            delay = RETRY_DELAYS[min(
                attempt,
                len(RETRY_DELAYS) - 1,
            )]
            time.sleep(delay)

    raise RuntimeError(
        "Geoportal przerwał połączenie po kilku próbach.\n\n"
        f"Adres: {url}\n"
        f"Szczegóły: {last_error}"
    )


def _http_get(url, timeout=HTTP_TIMEOUT):
    with _open_with_retry(url, timeout=timeout) as response:
        return (
            response.read(),
            response.headers.get_content_type(),
        )


def _local_name(tag):
    return tag.split("}", 1)[-1]


def _extract_download_url(payload, content_type):
    text = payload.decode(
        "utf-8",
        errors="ignore",
    )

    parser = _LinkParser()

    try:
        parser.feed(text)
    except Exception:
        LOGGER.debug("Optional compatibility operation failed.", exc_info=True)

    ranked = []

    for href, anchor in parser.links:
        low = (href + " " + anchor).lower()
        score = 0

        if ".zip" in low:
            score += 50

        if "powiat" in low:
            score += 100

        if "wojew" in low:
            score -= 20

        if "kraj" in low or "polsk" in low:
            score -= 40

        ranked.append(
            (score, href)
        )

    if ranked:
        ranked.sort(reverse=True)
        return urljoin(
            WMS_URL,
            ranked[0][1],
        )

    urls = re.findall(
        r'https?://[^\s"\'<>]+',
        text,
    )

    zip_urls = [
        url.rstrip(").,;")
        for url in urls
        if ".zip" in url.lower()
    ]

    if zip_urls:
        zip_urls.sort(
            key=lambda url: (
                "powiat" not in url.lower(),
                len(url),
            )
        )
        return zip_urls[0]

    raise RuntimeError(
        "Nie udało się znaleźć linku do paczki BDOT10k "
        "w odpowiedzi Geoportalu."
    )


def get_county_zip_url(
    x,
    y,
    bbox,
    crs_authid="EPSG:2180",
):
    """
    x, y - punkt zapytania w CRS bbox
    bbox - xmin, ymin, xmax, ymax
    """

    layer = WMS_QUERY_LAYER

    xmin, ymin, xmax, ymax = bbox

    width = 101
    height = 101

    px = int(round(
        (x - xmin)
        / (xmax - xmin)
        * (width - 1)
    ))

    py = int(round(
        (ymax - y)
        / (ymax - ymin)
        * (height - 1)
    ))

    px = max(
        0,
        min(width - 1, px),
    )

    py = max(
        0,
        min(height - 1, py),
    )

    params = {
        "SERVICE": "WMS",
        "VERSION": "1.1.1",
        "REQUEST": "GetFeatureInfo",
        "LAYERS": layer,
        "QUERY_LAYERS": layer,
        "STYLES": "",
        "SRS": crs_authid,
        "BBOX": f"{xmin},{ymin},{xmax},{ymax}",
        "WIDTH": width,
        "HEIGHT": height,
        "FORMAT": "image/png",
        "INFO_FORMAT": "text/html",
        "FEATURE_COUNT": 10,
        "X": px,
        "Y": py,
    }

    payload, content_type = _http_get(
        WMS_URL + "?" + urlencode(params)
    )

    return _extract_download_url(
        payload,
        content_type,
    )


def download_zip(
    url,
    progress_callback=None,
):
    """
    Pobiera ZIP z retry. Każdy URL dostaje osobny plik cache,
    więc przy wielu powiatach pliki nie nadpisują się przypadkowo.
    """

    cache_dir = os.path.join(
        tempfile.gettempdir(),
        "QuickBDOT",
        "downloads",
    )

    os.makedirs(
        cache_dir,
        exist_ok=True,
    )

    url_hash = hashlib.sha256(
        url.encode("utf-8")
    ).hexdigest()[:12]

    out_path = os.path.join(
        cache_dir,
        f"bdot10k_{url_hash}.zip",
    )

    temp_path = out_path + ".part"

    last_error = None

    for attempt in range(HTTP_RETRIES):
        try:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    LOGGER.debug("Temporary file cleanup failed.", exc_info=True)

            with _open_with_retry(
                url,
                timeout=180,
            ) as response, open(
                temp_path,
                "wb",
            ) as file_handle:

                total = int(
                    response.headers.get(
                        "Content-Length"
                    )
                    or 0
                )

                done = 0

                while True:
                    block = response.read(
                        1024 * 1024
                    )

                    if not block:
                        break

                    file_handle.write(block)
                    done += len(block)

                    if (
                        progress_callback
                        and total
                    ):
                        progress_callback(
                            int(
                                done
                                * 100
                                / total
                            )
                        )

            if not zipfile.is_zipfile(
                temp_path
            ):
                raise RuntimeError(
                    "Pobrany plik nie jest prawidłowym archiwum ZIP."
                )

            os.replace(
                temp_path,
                out_path,
            )

            return out_path

        except Exception as error:
            last_error = error

            if attempt >= HTTP_RETRIES - 1:
                break

            delay = RETRY_DELAYS[min(
                attempt,
                len(RETRY_DELAYS) - 1,
            )]

            time.sleep(delay)

    raise RuntimeError(
        "Nie udało się pobrać paczki BDOT10k po kilku próbach.\n\n"
        f"Szczegóły: {last_error}"
    )


def extract_selected_classes(
    zip_path,
    class_codes,
):
    extract_dir = os.path.join(
        tempfile.gettempdir(),
        "QuickBDOT",
        "selected",
    )

    if os.path.isdir(extract_dir):
        for root, dirs, files in os.walk(
            extract_dir,
            topdown=False,
        ):
            for name in files:
                try:
                    os.remove(
                        os.path.join(
                            root,
                            name,
                        )
                    )
                except OSError:
                    LOGGER.debug("Temporary file cleanup failed.", exc_info=True)

            for name in dirs:
                try:
                    os.rmdir(
                        os.path.join(
                            root,
                            name,
                        )
                    )
                except OSError:
                    LOGGER.debug("Temporary file cleanup failed.", exc_info=True)

    os.makedirs(
        extract_dir,
        exist_ok=True,
    )

    wanted = {
        code.upper()
        for code in class_codes
    }

    found = {}

    with zipfile.ZipFile(
        zip_path,
        "r",
    ) as archive:

        members = archive.namelist()

        for code in wanted:
            main_files = []

            for member in members:
                base = os.path.basename(
                    member
                )

                upper = base.upper()

                if (
                    code in upper
                    and upper.endswith(
                        (
                            ".SHP",
                            ".GML",
                            ".GPKG",
                        )
                    )
                ):
                    main_files.append(
                        member
                    )

            for main_member in main_files:
                base = os.path.basename(
                    main_member
                )

                stem = os.path.splitext(
                    base
                )[0]

                if base.upper().endswith(
                    ".SHP"
                ):
                    for member in members:
                        member_base = os.path.basename(
                            member
                        )

                        member_stem = os.path.splitext(
                            member_base
                        )[0]

                        if (
                            member_stem.lower()
                            == stem.lower()
                        ):
                            archive.extract(
                                member,
                                extract_dir,
                            )

                    shp_path = os.path.join(
                        extract_dir,
                        os.path.dirname(
                            main_member
                        ),
                        base,
                    )

                    found.setdefault(
                        code,
                        [],
                    ).append(
                        shp_path
                    )

                else:
                    archive.extract(
                        main_member,
                        extract_dir,
                    )

                    path = os.path.join(
                        extract_dir,
                        main_member,
                    )

                    found.setdefault(
                        code,
                        [],
                    ).append(
                        path
                    )

    return found
