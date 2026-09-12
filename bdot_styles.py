import logging
from qgis.PyQt.QtGui import QColor

from qgis.core import (
    QgsCategorizedSymbolRenderer,
    QgsFillSymbol,
    QgsRendererCategory,
    QgsSymbol,
    QgsWkbTypes,
)


LOGGER = logging.getLogger(__name__)

def _set_symbol_common(symbol, color, opacity=1.0):
    symbol.setColor(QColor(color))
    try:
        symbol.setOpacity(opacity)
    except Exception:
        LOGGER.debug("Optional compatibility operation failed.", exc_info=True)


def _set_line_width(symbol, width):
    try:
        symbol.setWidth(width)
        return
    except Exception:
        LOGGER.debug("Optional compatibility operation failed.", exc_info=True)

    try:
        layer = symbol.symbolLayer(0)
        if hasattr(layer, "setWidth"):
            layer.setWidth(width)
    except Exception:
        LOGGER.debug("Optional compatibility operation failed.", exc_info=True)


def _set_marker_size(symbol, size):
    try:
        symbol.setSize(size)
        return
    except Exception:
        LOGGER.debug("Optional compatibility operation failed.", exc_info=True)

    try:
        layer = symbol.symbolLayer(0)
        if hasattr(layer, "setSize"):
            layer.setSize(size)
    except Exception:
        LOGGER.debug("Optional compatibility operation failed.", exc_info=True)


def _set_outline(symbol, color, width=0.25):
    try:
        symbol_layer = symbol.symbolLayer(0)
    except Exception:
        return

    try:
        if hasattr(symbol_layer, "setStrokeColor"):
            symbol_layer.setStrokeColor(QColor(color))
    except Exception:
        LOGGER.debug("Optional compatibility operation failed.", exc_info=True)

    try:
        if hasattr(symbol_layer, "setStrokeWidth"):
            symbol_layer.setStrokeWidth(width)
    except Exception:
        LOGGER.debug("Optional compatibility operation failed.", exc_info=True)


def _single_symbol(layer, fill, outline=None, width=0.35, opacity=1.0, size=2.0):
    symbol = QgsSymbol.defaultSymbol(layer.geometryType())
    if symbol is None:
        return False

    _set_symbol_common(symbol, fill, opacity)

    geom = QgsWkbTypes.geometryType(layer.wkbType())

    if geom == QgsWkbTypes.GeometryType.LineGeometry:
        _set_line_width(symbol, width)
    elif geom == QgsWkbTypes.GeometryType.PointGeometry:
        _set_marker_size(symbol, size)
    elif geom == QgsWkbTypes.GeometryType.PolygonGeometry:
        _set_outline(symbol, outline or fill, width)

    layer.renderer().setSymbol(symbol)
    layer.triggerRepaint()
    return True


def _categorized(layer, field_name, definitions):
    if layer.fields().indexOf(field_name) < 0:
        return False

    geom = QgsWkbTypes.geometryType(layer.wkbType())
    categories = []

    for value, label, color, metric in definitions:
        symbol = QgsSymbol.defaultSymbol(layer.geometryType())
        if symbol is None:
            continue

        _set_symbol_common(symbol, color, 1.0)

        if geom == QgsWkbTypes.GeometryType.LineGeometry:
            _set_line_width(symbol, metric)
        elif geom == QgsWkbTypes.GeometryType.PointGeometry:
            _set_marker_size(symbol, metric)
        elif geom == QgsWkbTypes.GeometryType.PolygonGeometry:
            _set_outline(symbol, "#555555", 0.20)

        categories.append(
            QgsRendererCategory(value, symbol, label)
        )

    if not categories:
        return False

    layer.setRenderer(
        QgsCategorizedSymbolRenderer(
            field_name,
            categories,
        )
    )
    layer.triggerRepaint()
    return True


def _apply_builtin_style(layer, class_code):
    """
    Wbudowana symbolizacja QuickBDOT:
    czytelna prezentacja topograficzna bez zależności od zewnętrznych QML/SVG.
    """
    code = (class_code or "").upper()
    geom = QgsWkbTypes.geometryType(layer.wkbType())

    # Pokrycie terenu
    if code == "PTLZ":
        return _categorized(layer, "x_kod", [
            ("PTLZ01", "las", "#B7D79A", 0.20),
            ("PTLZ02", "zagajnik", "#C8E1AE", 0.20),
            ("PTLZ03", "zadrzewienie", "#D5E8C1", 0.20),
        ])

    if code == "PTWP":
        return _categorized(layer, "x_kod", [
            ("PTWP01", "woda morska", "#B9DFF4", 0.20),
            ("PTWP02", "woda płynąca", "#A9D8F2", 0.20),
            ("PTWP03", "woda stojąca", "#BFE3F6", 0.20),
        ])

    if code == "PTZB":
        return _single_symbol(layer, "#E6D9CF", "#B8AAA0", 0.20, 0.85)

    if code in ("PTTR", "PTUT"):
        return _single_symbol(layer, "#E7E2B2", "#CFC995", 0.15, 0.75)

    if code == "PTRK":
        return _single_symbol(layer, "#D2E4B7", "#AABE94", 0.15, 0.80)

    if code in ("PTGN", "PTNZ"):
        return _single_symbol(layer, "#EEE9DF", "#C8C0B5", 0.15, 0.75)

    if code in ("PTKM", "PTPL"):
        return _single_symbol(layer, "#E5E5E5", "#B7B7B7", 0.20, 0.90)

    if code in ("PTSO", "PTWZ"):
        return _single_symbol(layer, "#D9C8B0", "#9C8C77", 0.20, 0.85)

    # Sieć wodna
    if code in ("SWRS", "SWKN"):
        return _single_symbol(layer, "#2387C9", width=0.60)

    if code == "SWRM":
        return _single_symbol(layer, "#4B9CD3", width=0.35)

    # Drogi / jezdnie
    if code in ("SKDR", "SKJZ"):
        return _categorized(layer, "x_kod", [
            (f"{code}01", "autostrada", "#D95F43", 1.40),
            (f"{code}02", "droga ekspresowa", "#E58B45", 1.25),
            (f"{code}03", "droga GP", "#E7A152", 1.05),
            (f"{code}04", "droga główna", "#E9B968", 0.90),
            (f"{code}05", "droga zbiorcza", "#F1CE84", 0.75),
            (f"{code}06", "droga lokalna", "#F2E0B6", 0.60),
            (f"{code}07", "droga dojazdowa", "#F4F0E7", 0.45),
            (f"{code}08", "droga inna", "#D8D8D8", 0.35),
        ])

    if code == "SKTR":
        return _single_symbol(layer, "#4D4D4D", width=0.55)

    if code == "SKRP":
        return _single_symbol(layer, "#AA7A45", width=0.40)

    if code in ("SKRW", "SKPP"):
        return _single_symbol(layer, "#C97B4A", width=0.55, size=2.2)

    # Uzbrojenie
    if code == "SULN":
        return _single_symbol(layer, "#6B6B6B", width=0.35)

    if code == "SUPR":
        return _single_symbol(layer, "#B35C82", width=0.35)

    # Budynki / budowle
    if code == "BUBD":
        return _single_symbol(layer, "#D8B7A7", "#8B6F62", 0.30, 1.0)

    if code in ("BUIN", "BUHD", "BUUO", "BUZM"):
        return _single_symbol(layer, "#7B7B7B", "#575757", 0.40, 1.0, 2.0)

    if code in ("BUSP", "BUZT"):
        return _single_symbol(layer, "#D6D6D6", "#777777", 0.25, 0.90, 2.2)

    if code in ("BUWT", "BUIT", "BUIB", "BUTR", "BUCM"):
        return _single_symbol(layer, "#5E5E5E", "#444444", 0.30, 1.0, 2.4)

    # Kompleksy użytkowania
    if code.startswith("KU"):
        return _single_symbol(layer, "#EAE3D6", "#BDB2A3", 0.18, 0.55)

    # Tereny chronione / administracja
    if code.startswith("TC"):
        return _single_symbol(layer, "#CDE5C4", "#6C9B62", 0.35, 0.28)

    if code == "ADJA":
        return _single_symbol(layer, "#FFFFFF", "#777777", 0.35, 0.03)

    if code == "ADMS":
        if geom == QgsWkbTypes.GeometryType.PolygonGeometry:
            symbol = QgsFillSymbol.createSimple({
                "color": "255,255,255,0",
                "outline_color": "105,105,105,210",
                "outline_width": "0.28",
                "outline_style": "dash",
            })
            layer.renderer().setSymbol(symbol)
            layer.triggerRepaint()
            return True

        if geom == QgsWkbTypes.GeometryType.LineGeometry:
            return _single_symbol(layer, "#707070", width=0.28)

        return _single_symbol(layer, "#565656", size=1.8)

    # Obiekty inne
    if code == "OIMK":
        return _single_symbol(layer, "#BBD8CE", "#77A99A", 0.18, 0.65)

    if code == "OISZ":
        return _single_symbol(layer, "#B5D6BE", "#7AAA87", 0.18, 0.65)

    if code in ("OIOR", "OIKM", "OIPR"):
        if geom == QgsWkbTypes.GeometryType.PointGeometry:
            return _single_symbol(layer, "#333333", size=2.4)
        if geom == QgsWkbTypes.GeometryType.LineGeometry:
            return _single_symbol(layer, "#555555", width=0.40)
        return _single_symbol(layer, "#D4D4D4", "#666666", 0.25, 0.80)

    return False


from pathlib import Path
import re
import tempfile

_PRIMARY_QML = {
    ("ADJA", "A"): 'OT_ADJA_A [25-29].qml',
    ("BUBD", "A"): 'OT_BUBD_A [42].qml',
    ("BUHD", "A"): 'OT_BUHD_A [49].qml',
    ("BUHD", "L"): 'OT_BUHD_L [49].qml',
    ("BUIB", "A"): 'OT_BUIB_A [41].qml',
    ("BUIB", "L"): 'OT_BUIB_L [41].qml',
    ("BUIN", "L"): 'OT_BUIN_L [46].qml',
    ("BUIT", "A"): 'OT_BUIT_A [57-58].qml',
    ("BUIT", "P"): 'OT_BUIT_P [58].qml',
    ("BUSP", "A"): 'OT_BUSP_A [19].qml',
    ("BUSP", "L"): 'OT_BUSP_L [20].qml',
    ("BUTR", "L"): 'OT_BUTR_L [51].qml',
    ("BUTR", "P"): 'OT_BUTR_P [54].qml',
    ("BUUO", "L"): 'OT_BUUO_L [45].qml',
    ("BUWT", "A"): 'OT_BUWT_A [42].qml',
    ("BUWT", "P"): 'OT_BUWT_P [59].qml',
    ("BUZM", "L"): 'OT_BUZM_L [7].qml',
    ("BUZT", "A"): 'OT_BUZT_A [55].qml',
    ("BUZT", "P"): 'OT_BUZT_P [56].qml',
    ("KUKO", "P"): 'OT_KUKO_P [61].qml',
    ("KUPG", "A"): 'OT_KUPG_A [4].qml',
    ("KUSC", "A"): 'OT_KUSC_A [16].qml',
    ("OIKM", "L"): 'OT_OIKM_L [39].qml',
    ("OIKM", "P"): 'OT_OIKM_P [61].qml',
    ("OIMK", "A"): 'OT_OIMK_A [10].qml',
    ("OIOR", "A"): 'OT_OIOR_A [42].qml',
    ("OIOR", "L"): 'OT_OIOR_L [44].qml',
    ("OIOR", "P"): 'OT_OIOR_P [60].qml',
    ("OIPR", "L"): 'OT_OIPR_L [17-18].qml',
    ("OIPR", "P"): 'OT_OIPR_P [50].qml',
    ("OISZ", "A"): 'OT_OISZ_A [15].qml',
    ("PTGN", "A"): 'OT_PTGN_A [1].qml',
    ("PTKM", "A"): 'OT_PTKM_A [11].qml',
    ("PTLZ", "A"): 'OT_PTLZ_A [0].qml',
    ("PTPL", "A"): 'OT_PTPL_A [11].qml',
    ("PTRK", "A"): 'OT_PTRK_A [0].qml',
    ("PTSO", "A"): 'OT_PTSO_A [3].qml',
    ("PTTR", "A"): 'OT_PTTR_A [0].qml',
    ("PTUT", "A"): 'OT_PTUT_A [0].qml',
    ("PTWP", "A"): 'OT_PTWP_A [13].qml',
    ("PTWZ", "A"): 'OT_PTWZ_A [1].qml',
    ("PTZB", "A"): 'OT_PTZB_A roslinnosc [0].qml',
    ("SKDR", "L"): 'OT_SKDR_L [32].qml',
    ("SKJZ", "L"): 'OT_SKJZ_L [31].qml',
    ("SKPP", "L"): 'OT_SKPP_L [48].qml',
    ("SKRP", "L"): 'OT_SKRP_L [30].qml',
    ("SKTR", "L"): 'OT_SKTR_L [40].qml',
    ("SULN", "L"): 'OT_SULN_L [53].qml',
    ("SUPR", "L"): 'OT_SUPR_L [52].qml',
    ("SWKN", "L"): 'OT_SWKN_L [12].qml',
    ("SWRM", "L"): 'OT_SWRM_L [12].qml',
    ("SWRS", "L"): 'OT_SWRS_L [12].qml',
    ("TCON", "A"): 'OT_TCON_A.qml',
    ("TCPK", "A"): 'OT_TCPK_A [22].qml',
    ("TCPN", "A"): 'OT_TCPN_A [24].qml',
    ("TCRZ", "A"): 'OT_TCRZ_A [23].qml',
}


def _geometry_suffix(layer):
    geom = QgsWkbTypes.geometryType(layer.wkbType())
    if geom == QgsWkbTypes.GeometryType.PointGeometry:
        return "P"
    if geom == QgsWkbTypes.GeometryType.LineGeometry:
        return "L"
    if geom == QgsWkbTypes.GeometryType.PolygonGeometry:
        return "A"
    return None


def _patch_qml_paths(qml_text, svg_root):
    """
    Zamienia względne i stare absolutne ścieżki SVG z oryginalnej wtyczki
    na ścieżki do zasobów znajdujących się wewnątrz QuickBDOT.
    """
    svg_root = str(svg_root).replace("\\", "/")
    karto = f"{svg_root}/KARTO10k/"

    # Względne ścieżki zapisane jako KARTO10k/plik.svg
    qml_text = qml_text.replace("KARTO10k/", karto)

    # Stare ścieżki absolutne z profili autorów/użytkowników.
    qml_text = re.sub(
        r'[A-Za-z]:/[^<>"\']*?/BDOT10k_SVG/KARTO10k/',
        karto,
        qml_text,
        flags=re.IGNORECASE,
    )
    return qml_text


def _load_packaged_qml(layer, class_code):
    geom = _geometry_suffix(layer)
    if not geom:
        return False

    qml_name = _PRIMARY_QML.get(((class_code or "").upper(), geom))
    if not qml_name:
        return False

    plugin_dir = Path(__file__).resolve().parent
    qml_path = plugin_dir / "assets" / "qml" / qml_name
    svg_root = plugin_dir / "assets" / "svg"

    if not qml_path.is_file():
        return False

    try:
        text = qml_path.read_text(encoding="utf-8", errors="ignore")
        text = _patch_qml_paths(text, svg_root)

        cache_dir = Path(tempfile.gettempdir()) / "QuickBDOT" / "qml_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)

        cache_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", qml_name)
        patched = cache_dir / cache_name
        patched.write_text(text, encoding="utf-8")

        result = layer.loadNamedStyle(str(patched))
        success = True
        if isinstance(result, tuple) and len(result) >= 2:
            success = bool(result[1])

        if success:
            layer.triggerRepaint()
            return True
    except Exception:
        return False

    return False


def apply_bdot_style(layer, class_code):
    """
    Najpierw używa dostarczonego stylu QML z BDOT10k_GML_SHP_Loader 2.0.1.
    Jeśli dla danej klasy/geometrii nie ma odpowiedniego QML albo QGIS
    nie może go załadować, stosuje styl awaryjny QuickBDOT.
    """
    if _load_packaged_qml(layer, class_code):
        return True

    return _apply_builtin_style(layer, class_code)


def apply_auxiliary_qml(layer, qml_name):
    """
    Ładuje pomocniczy styl QML z paczki QuickBDOT.
    Używane dla etykiet i dodatkowych reprezentacji dróg/kolei.
    """
    plugin_dir = Path(__file__).resolve().parent
    qml_path = plugin_dir / "assets" / "qml" / qml_name
    svg_root = plugin_dir / "assets" / "svg"

    if not qml_path.is_file():
        return False

    try:
        text = qml_path.read_text(encoding="utf-8", errors="ignore")
        text = _patch_qml_paths(text, svg_root)

        cache_dir = Path(tempfile.gettempdir()) / "QuickBDOT" / "qml_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)

        cache_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", qml_name)
        patched = cache_dir / ("aux_" + cache_name)
        patched.write_text(text, encoding="utf-8")

        result = layer.loadNamedStyle(str(patched))
        success = True
        if isinstance(result, tuple) and len(result) >= 2:
            success = bool(result[1])

        if success:
            layer.triggerRepaint()
            return True

    except Exception:
        return False

    return False
