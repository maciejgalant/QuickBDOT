import logging
import json
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from qgis.PyQt.QtCore import QObject, QMetaType, pyqtSignal
from qgis.PyQt.QtGui import QColor

from qgis.core import (
    QgsArcGisRestUtils,
    QgsFeature,
    QgsField,
    QgsGeometry,
    QgsProject,
    QgsVectorLayer,
)

from qgis.gui import QgsMapToolIdentifyFeature


LOGGER = logging.getLogger(__name__)

POWIATY_QUERY_URL = (
    "https://mapy.geoportal.gov.pl/wss/ims/maps/"
    "PRG_gugik_wyszukiwarka/FeatureServer/1/query"
)


def _validated_prg_url(url):
    parsed = urlparse(str(url))
    hostname = (parsed.hostname or "").lower()
    if parsed.scheme.lower() != "https":
        raise ValueError("PRG URL must use HTTPS.")
    if hostname != "mapy.geoportal.gov.pl":
        raise ValueError("Unexpected PRG service host.")
    return parsed.geturl()


class AdminIdentifyTool(QgsMapToolIdentifyFeature):

    featureToggled = pyqtSignal()

    def __init__(self, canvas, layer):
        super().__init__(canvas, layer)

        self.layer = layer

        self.featureIdentified.connect(
            self._toggle_feature
        )

    def _toggle_feature(self, feature):

        selected = set(
            self.layer.selectedFeatureIds()
        )

        fid = feature.id()

        if fid in selected:
            selected.remove(fid)
        else:
            selected.add(fid)

        self.layer.selectByIds(
            list(selected)
        )

        self.featureToggled.emit()


class AdminSelector(QObject):

    selectionChanged = pyqtSignal(list)

    def __init__(self, iface):
        super().__init__()

        self.iface = iface
        self.canvas = iface.mapCanvas()

        self.layer = None
        self.map_tool = None
        self.previous_map_tool = None

        self._county_records = None

    # -------------------------------------------------
    # POBIERANIE PRG
    # -------------------------------------------------

    def _download_powiaty(self):

        params = {
            "where": "1=1",
            "outFields": "id,teryt,nazwa",
            "returnGeometry": "true",
            "outSR": "2180",
            "f": "json",
        }

        url = (
            POWIATY_QUERY_URL
            + "?"
            + urlencode(params)
        )

        url = _validated_prg_url(url)

        request = Request(
            url,
            headers={
                "User-Agent": "QuickBDOT/0.0.38 QGIS",
                "Accept": "application/json,text/plain,*/*",
            },
        )

        try:

            with urlopen(  # nosec B310 - fixed HTTPS Geoportal PRG endpoint
                request,
                timeout=45
            ) as response:

                payload = response.read()

        except Exception as error:

            raise RuntimeError(
                "Nie udało się pobrać granic powiatów PRG.\n\n"
                f"Szczegóły: {error}"
            )

        try:

            data = json.loads(
                payload.decode("utf-8")
            )

        except Exception as error:

            raise RuntimeError(
                "Nie udało się odczytać odpowiedzi PRG.\n\n"
                f"Szczegóły: {error}"
            )

        if "error" in data:

            raise RuntimeError(
                "Usługa PRG zwróciła błąd:\n"
                + json.dumps(
                    data["error"],
                    ensure_ascii=False,
                    indent=2
                )
            )

        features = data.get(
            "features",
            []
        )

        if not features:

            raise RuntimeError(
                "Usługa PRG nie zwróciła powiatów."
            )

        return features

    # -------------------------------------------------
    # CACHE POWIATÓW
    # -------------------------------------------------

    def _county_records_from_rest(self):

        if self._county_records is not None:
            return self._county_records

        rest_features = self._download_powiaty()

        records = []

        for item in rest_features:

            attrs = item.get(
                "attributes",
                {}
            )

            esri_geometry = item.get(
                "geometry"
            )

            if not esri_geometry:
                continue

            converted = QgsArcGisRestUtils.convertGeometry(
                esri_geometry,
                "esriGeometryPolygon",
                False,
                False,
            )

            if isinstance(
                converted,
                tuple
            ):
                abstract_geometry = converted[0]

            else:
                abstract_geometry = converted

            if abstract_geometry is None:
                continue

            geometry = QgsGeometry(
                abstract_geometry
            )

            if (
                geometry.isNull()
                or geometry.isEmpty()
            ):
                continue

            records.append(
                {
                    "id": attrs.get("id"),
                    "teryt": str(
                        attrs.get(
                            "teryt",
                            ""
                        )
                    ),
                    "name": str(
                        attrs.get(
                            "nazwa",
                            ""
                        )
                    ),
                    "geometry": geometry,
                }
            )

        if not records:

            raise RuntimeError(
                "Nie udało się utworzyć geometrii powiatów."
            )

        self._county_records = records

        return records

    # -------------------------------------------------
    # POWIATY PRZECINAJĄCE MASKĘ
    # -------------------------------------------------

    def intersecting_units(
        self,
        mask_geometry
    ):

        if (
            mask_geometry is None
            or mask_geometry.isNull()
            or mask_geometry.isEmpty()
        ):
            return []

        result = []

        for record in self._county_records_from_rest():

            county_geometry = record[
                "geometry"
            ]

            try:

                intersects = (
                    county_geometry
                    .intersects(
                        mask_geometry
                    )
                )

            except Exception:

                intersects = False

            if not intersects:
                continue

            result.append(
                {
                    "fid": record["id"],
                    "name": record["name"],
                    "teryt": record["teryt"],
                    "geometry": QgsGeometry(
                        county_geometry
                    ),
                }
            )

        result.sort(
            key=lambda item:
            item["name"].lower()
        )

        return result

    # -------------------------------------------------
    # WARSTWA POWIATÓW
    # -------------------------------------------------

    def show_counties(self):

        self.stop_selection(
            remove_layer=True
        )

        layer = QgsVectorLayer(
            "MultiPolygon?crs=EPSG:2180",
            "QuickBDOT – Powiaty",
            "memory",
        )

        provider = layer.dataProvider()

        provider.addAttributes(
            [
                QgsField(
                    "id",
                    QMetaType.Type.Int
                ),

                QgsField(
                    "teryt",
                    QMetaType.Type.QString
                ),

                QgsField(
                    "nazwa",
                    QMetaType.Type.QString
                ),
            ]
        )

        layer.updateFields()

        records = (
            self._county_records_from_rest()
        )

        qgis_features = []

        for record in records:

            feature = QgsFeature(
                layer.fields()
            )

            feature.setGeometry(
                QgsGeometry(
                    record["geometry"]
                )
            )

            feature.setAttributes(
                [
                    record["id"],
                    record["teryt"],
                    record["name"],
                ]
            )

            qgis_features.append(
                feature
            )

        provider.addFeatures(
            qgis_features
        )

        layer.updateExtents()

        # Styl pomocniczy
        symbol = (
            layer.renderer()
            .symbol()
        )

        if symbol is not None:

            symbol.setColor(
                QColor(
                    110,
                    110,
                    110,
                    35
                )
            )

            symbol_layer = (
                symbol.symbolLayer(0)
            )

            if symbol_layer is not None:

                try:

                    symbol_layer.setStrokeColor(
                        QColor(
                            70,
                            70,
                            70,
                            200
                        )
                    )

                    symbol_layer.setStrokeWidth(
                        0.6
                    )

                except Exception:
                    LOGGER.debug("Optional compatibility operation failed.", exc_info=True)

        QgsProject.instance().addMapLayer(
            layer
        )

        self.layer = layer

        try:

            self.canvas.setSelectionColor(
                QColor(
                    255,
                    255,
                    0,
                    220
                )
            )

        except Exception:
            LOGGER.debug("Optional compatibility operation failed.", exc_info=True)

        self.previous_map_tool = (
            self.canvas.mapTool()
        )

        self.map_tool = (
            AdminIdentifyTool(
                self.canvas,
                self.layer
            )
        )

        self.map_tool.featureToggled.connect(
            self._emit_selection
        )

        self.canvas.setMapTool(
            self.map_tool
        )

        self._emit_selection()

        return layer

    # -------------------------------------------------
    # CZYSZCZENIE SELEKCJI
    # -------------------------------------------------

    def clear_selection(self):

        if self.layer is None:
            return

        self.layer.removeSelection()

        self._emit_selection()

    # -------------------------------------------------
    # WYBRANE POWIATY
    # -------------------------------------------------

    def selected_units(self):

        if self.layer is None:
            return []

        result = []

        for feature in (
            self.layer.selectedFeatures()
        ):

            result.append(
                {
                    "fid": feature.id(),
                    "name": str(
                        feature["nazwa"]
                    ),
                    "teryt": str(
                        feature["teryt"]
                    ),
                    "geometry": QgsGeometry(
                        feature.geometry()
                    ),
                }
            )

        result.sort(
            key=lambda item:
            item["name"].lower()
        )

        return result

    # -------------------------------------------------
    # SYGNAŁ
    # -------------------------------------------------

    def _emit_selection(self):

        self.selectionChanged.emit(
            self.selected_units()
        )

    # -------------------------------------------------
    # WYŁĄCZENIE NARZĘDZIA
    # -------------------------------------------------

    def stop_selection(
        self,
        remove_layer=False
    ):

        if self.map_tool is not None:

            try:

                if (
                    self.canvas.mapTool()
                    == self.map_tool
                ):

                    if (
                        self.previous_map_tool
                        is not None
                    ):

                        self.canvas.setMapTool(
                            self.previous_map_tool
                        )

                    else:

                        self.canvas.unsetMapTool(
                            self.map_tool
                        )

            except Exception:
                LOGGER.debug("Optional compatibility operation failed.", exc_info=True)

        self.map_tool = None
        self.previous_map_tool = None

        if (
            remove_layer
            and self.layer is not None
        ):

            try:

                QgsProject.instance().removeMapLayer(
                    self.layer.id()
                )

            except Exception:
                LOGGER.debug("Optional compatibility operation failed.", exc_info=True)

            self.layer = None

        self._emit_selection()
