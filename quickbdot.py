import re
import tempfile
import urllib.request
from pathlib import Path

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QFont, QColor, QIcon, QPixmap
from qgis.PyQt.QtWidgets import (
    QWidget,
    QAction,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)

from qgis.core import (
    Qgis,
    QgsNullSymbolRenderer,
    QgsPalLayerSettings,
    QgsTextBufferSettings,
    QgsTextFormat,
    QgsVectorLayerSimpleLabeling,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeature,
    QgsFeatureRequest,
    QgsGeometry,
    QgsProject,
    QgsRectangle,
    QgsVectorLayer,
    QgsVectorFileWriter,
    QgsWkbTypes,
)

import processing

from .bdot_catalog import BDOT_TREE
from .bdot_styles import apply_bdot_style, apply_auxiliary_qml
from .downloader import (
    get_county_zip_url,
    download_zip,
    extract_selected_classes,
)
from .admin_selector import AdminSelector


class QuickBDOTDialog(QDialog):

    def __init__(self, iface, parent=None):
        super().__init__(parent)

        self.iface = iface
        self.admin_selector = AdminSelector(iface)
        self.admin_selector.selectionChanged.connect(
            self.update_admin_selection_label
        )

        self.setWindowTitle("QuickBDOT 0.0.37")

        plugin_icon_path = (
            Path(__file__).resolve().parent
            / "icons"
            / "quickbdot_logo.png"
        )
        if plugin_icon_path.is_file():
            self.setWindowIcon(QIcon(str(plugin_icon_path)))

        self.resize(620, 690)
        self.setMinimumWidth(520)
        self.setMinimumHeight(480)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # -------------------------------------------------
        # STAŁY NAGŁÓWEK
        # -------------------------------------------------

        header_widget = QWidget()
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(10, 8, 10, 6)
        header_layout.setSpacing(4)

        header_row = QHBoxLayout()
        header_row.setSpacing(8)

        self.logo_label = QLabel()
        self.logo_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft
            | Qt.AlignmentFlag.AlignVCenter
        )

        interface_logo_path = (
            Path(__file__).resolve().parent
            / "icons"
            / "quickbdot_logo.png"
        )

        if interface_logo_path.is_file():
            interface_icon = QIcon(str(interface_logo_path))
            self.logo_label.setPixmap(
                interface_icon.pixmap(132, 132)
            )
            self.logo_label.setMinimumSize(132, 132)
        else:
            self.logo_label.setText("<b>QuickBDOT</b>")

        header_row.addWidget(self.logo_label)
        header_row.addStretch(1)

        self.help_btn = QPushButton("?")
        self.help_btn.setFixedSize(32, 32)
        self.help_btn.setToolTip(
            "Instrukcja, funkcje i informacje o wtyczce"
        )
        self.help_btn.clicked.connect(self.show_help_dialog)
        header_row.addWidget(self.help_btn)

        header_layout.addLayout(header_row)

        intro = QLabel(
            "Selekcja. Pobieranie. Zapis. Stylizacja. BDOT10k w jednym miejscu."
        )
        intro.setWordWrap(True)
        header_layout.addWidget(intro)

        outer_layout.addWidget(header_widget)

        # -------------------------------------------------
        # PRZEWIJANA CZĘŚĆ INTERFEJSU
        # -------------------------------------------------

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )

        content_widget = QWidget()
        content_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.MinimumExpanding,
        )

        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(10, 4, 10, 10)
        layout.setSpacing(7)

        self.scroll_area.setWidget(content_widget)
        outer_layout.addWidget(self.scroll_area)

        # -------------------------------------------------
        # OBSZAR
        # -------------------------------------------------

        area_group = QGroupBox("Wybór obszaru:")
        area_layout = QVBoxLayout(area_group)
        area_layout.setContentsMargins(9, 8, 9, 8)
        area_layout.setSpacing(5)

        self.extent_radio = QRadioButton(
            "Zasięg bieżącego widoku"
        )
        self.vector_radio = QRadioButton(
            "Warstwa poligonowa"
        )
        self.county_radio = QRadioButton(
            "Powiaty – wybór na mapie"
        )

        self.extent_radio.setToolTip(
            "Pobiera dane BDOT10k dla obszaru aktualnie widocznego "
            "w oknie mapy QGIS."
        )
        self.vector_radio.setToolTip(
            "Pobiera dane BDOT10k i przycina je do geometrii "
            "wskazanej warstwy poligonowej z projektu."
        )
        self.county_radio.setToolTip(
            "Umożliwia wskazanie jednego lub wielu powiatów "
            "bezpośrednio na mapie i pobranie danych dla wybranego obszaru."
        )

        self.extent_radio.setChecked(True)

        self.extent_radio.toggled.connect(self.update_area_mode)
        self.vector_radio.toggled.connect(self.update_area_mode)
        self.county_radio.toggled.connect(self.update_area_mode)

        area_layout.addWidget(self.extent_radio)
        area_layout.addWidget(self.vector_radio)
        area_layout.addWidget(self.county_radio)

        self.vector_layer_combo = QComboBox()
        self.vector_layer_combo.setEnabled(False)
        self.vector_layer_combo.setToolTip(
            "Warstwa poligonowa używana jako maska obszaru pobierania."
        )
        area_layout.addWidget(self.vector_layer_combo)

        admin_buttons = QHBoxLayout()
        admin_buttons.setSpacing(6)

        self.show_admin_btn = QPushButton(
            "Wybierz powiaty na mapie"
        )
        self.show_admin_btn.clicked.connect(self.show_admin_areas)
        self.show_admin_btn.setEnabled(False)

        self.clear_admin_btn = QPushButton(
            "Wyczyść wybór powiatów"
        )
        self.clear_admin_btn.clicked.connect(
            self.admin_selector.clear_selection
        )
        self.clear_admin_btn.setEnabled(False)

        admin_buttons.addWidget(self.show_admin_btn)
        admin_buttons.addWidget(self.clear_admin_btn)
        area_layout.addLayout(admin_buttons)

        self.admin_selection_label = QLabel("")
        self.admin_selection_label.setVisible(False)

        layout.addWidget(area_group)

        # -------------------------------------------------
        # WARSTWY BDOT10k
        # -------------------------------------------------

        class_group = QGroupBox("Selekcja warstw BDOT10k:")
        class_layout = QVBoxLayout(class_group)
        class_layout.setContentsMargins(9, 8, 9, 8)
        class_layout.setSpacing(5)

        tree_toolbar = QHBoxLayout()
        tree_toolbar.setSpacing(5)

        self.select_all_btn = QPushButton("Zaznacz wszystko")
        self.clear_tree_btn = QPushButton("Wyczyść")
        self.expand_tree_btn = QPushButton("Rozwiń")
        self.collapse_tree_btn = QPushButton("Zwiń")

        self.select_all_btn.clicked.connect(self._select_all_tree)
        self.clear_tree_btn.clicked.connect(self._clear_tree_selection)
        self.expand_tree_btn.clicked.connect(self._expand_tree)
        self.collapse_tree_btn.clicked.connect(self._collapse_tree)

        tree_toolbar.addWidget(self.select_all_btn)
        tree_toolbar.addWidget(self.clear_tree_btn)
        tree_toolbar.addStretch(1)
        tree_toolbar.addWidget(self.expand_tree_btn)
        tree_toolbar.addWidget(self.collapse_tree_btn)
        class_layout.addLayout(tree_toolbar)

        self.class_tree = QTreeWidget()
        self.class_tree.setToolTip(
            "Poziom 1 = kategoria, poziom 2 = klasa, poziom 3 = typ obiektu. "
            "Możesz zaznaczyć całą kategorię lub klasę albo rozwinąć gałąź "
            "i wybrać tylko konkretne typy obiektów."
        )
        self.class_tree.setHeaderLabels(["Kod / nazwa"])
        self.class_tree.setRootIsDecorated(True)
        self.class_tree.setAlternatingRowColors(True)
        self.class_tree.setUniformRowHeights(True)
        self.class_tree.setMinimumHeight(100)
        self.class_tree.setMaximumHeight(460)
        self.class_tree.itemChanged.connect(self._on_tree_item_changed)
        self.class_tree.itemExpanded.connect(self._update_tree_height)
        self.class_tree.itemCollapsed.connect(self._update_tree_height)
        self._tree_updating = False

        self._build_bdot_tree()
        class_layout.addWidget(self.class_tree)

        layout.addWidget(class_group)

        # -------------------------------------------------
        # PREZENTACJA
        # -------------------------------------------------

        format_group = QGroupBox("Prezentacja danych:")
        format_layout = QVBoxLayout(format_group)
        format_layout.setContentsMargins(9, 8, 9, 8)
        format_layout.setSpacing(5)

        self.gpkg_radio = QRadioButton()
        self.shp_radio = QRadioButton()
        self.gpkg_radio.setChecked(True)
        self.gpkg_radio.hide()
        self.shp_radio.hide()

        self.apply_styles_checkbox = QCheckBox(
            "Zastosuj etykiety i symbolizację"
        )
        self.apply_styles_checkbox.setChecked(True)
        format_layout.addWidget(self.apply_styles_checkbox)
        layout.addWidget(format_group)

        # -------------------------------------------------
        # ZAPIS
        # -------------------------------------------------

        output_group = QGroupBox("Zapis:")
        output_layout = QVBoxLayout(output_group)
        output_layout.setContentsMargins(9, 8, 9, 8)
        output_layout.setSpacing(5)

        path_layout = QHBoxLayout()
        path_layout.setSpacing(6)

        self.output_path = QLineEdit()
        self.output_path.setPlaceholderText(
            "Nazwa pliku .gpkg lub .shp..."
        )
        self.output_path.textChanged.connect(
            self._detect_output_format
        )

        self.browse_btn = QPushButton("Wybierz…")
        self.browse_btn.clicked.connect(self.choose_output)

        path_layout.addWidget(self.output_path, 1)
        path_layout.addWidget(self.browse_btn)
        output_layout.addLayout(path_layout)

        self.output_hint = QLabel(
            "Format zostanie rozpoznany po rozszerzeniu: .gpkg lub .shp."
        )
        self.output_hint.setWordWrap(True)
        output_layout.addWidget(self.output_hint)

        layout.addWidget(output_group)

        # -------------------------------------------------
        # STATUS I POSTĘP
        # -------------------------------------------------

        progress_row = QHBoxLayout()
        progress_row.setSpacing(8)

        # Status jest elementem interfejsu, a nie osobnym oknem.
        self.status = QLabel(self)
        self.status.setText("")
        self.status.setMinimumWidth(0)
        self.status.setMaximumWidth(240)
        self.status.setWordWrap(False)
        self.status.setVisible(False)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)

        progress_row.addWidget(self.status)
        progress_row.addWidget(self.progress, 1)
        layout.addLayout(progress_row)

        # Wynik procesu i lista brakujących elementów.
        # Pole jest przewijane i pojawia się dopiero po zakończeniu
        # albo po wystąpieniu błędu.
        self.result_details = QPlainTextEdit(self)
        self.result_details.setReadOnly(True)
        self.result_details.setPlaceholderText(
            "Szczegóły procesu pojawią się tutaj po zakończeniu."
        )
        self.result_details.setMaximumHeight(170)
        self.result_details.setMinimumHeight(90)
        self.result_details.setVisible(False)
        layout.addWidget(self.result_details)

        self.download_btn = QPushButton("Pobierz i zapisz")
        self.download_btn.setMinimumHeight(38)
        font = self.download_btn.font()
        font.setBold(True)
        self.download_btn.setFont(font)
        self.download_btn.clicked.connect(self.start_download)
        layout.addWidget(self.download_btn)

        self.refresh_vector_layers()
        self._update_tree_height()

    # -------------------------------------------------
    # OBSZAR
    # -------------------------------------------------

    def show_help_dialog(self):
        text = (
            "<b>QuickBDOT 0.0.37</b><br><br>"
            "<b>Opis wtyczki</b><br>"
            "QuickBDOT to wtyczka do QGIS przeznaczona do sprawnego pobierania, "
            "selekcji, zapisu i wizualizacji danych BDOT10k. Umożliwia określenie "
            "obszaru opracowania na kilka sposobów oraz automatyzuje przygotowanie "
            "warstw do dalszej pracy w projekcie GIS.<br><br>"

            "<b>Najważniejsze funkcje:</b><br>"
            "• pobieranie danych BDOT10k dla bieżącego zasięgu mapy,<br>"
            "• pobieranie danych na podstawie geometrii wybranej warstwy poligonowej,<br>"
            "• przestrzenny wybór powiatów bezpośrednio na mapie,<br>"
            "• trzystopniowa selekcja klas i typów obiektów BDOT10k,<br>"
            "• zapis danych do formatu GeoPackage lub Shapefile,<br>"
            "• automatyczne porządkowanie kolejności warstw w projekcie,<br>"
            "• opcjonalne zastosowanie symbolizacji i etykiet właściwych dla danych BDOT10k.<br><br>"

            "<b>Sposób użycia:</b><br>"
            "1. Wybierz metodę określenia obszaru opracowania.<br>"
            "2. Zaznacz wymagane klasy i warstwy BDOT10k.<br>"
            "3. Wskaż lokalizację oraz nazwę pliku wynikowego .gpkg lub .shp "
            "albo użyj przycisku Wybierz.<br>"
            "4. W razie potrzeby pozostaw włączoną automatyczną symbolizację "
            "i etykietowanie.<br>"
            "5. Kliknij <b>Pobierz i zapisz</b>, aby rozpocząć przetwarzanie danych.<br><br>"

            "<b>Informacje o projekcie</b><br>"
            "Autor: Maciej Galant<br>"
            "Wersja: 0.0.37<br>"
            "Rok: 2026<br><br>"

            "<b>Prawa autorskie i licencja</b><br>"
            "QuickBDOT jest rozwijany jako wtyczka dla środowiska QGIS. "
            "Część zasobów kartograficznych wykorzystywanych do symbolizacji, "
            "w szczególności pliki QML i SVG, pochodzi z projektu "
            "BDOT10k_GML_SHP_Loader 2.0.1 i jest wykorzystywana zgodnie "
            "z warunkami licencji GNU General Public License (GNU GPL).<br><br>"

            "Szczegółowe informacje dotyczące licencji, praw autorskich oraz "
            "pochodzenia wykorzystanych zasobów znajdują się w plikach "
            "LICENSE oraz NOTICE.txt dołączonych do wtyczki."
        )

        box = QMessageBox(self)
        box.setWindowTitle("QuickBDOT — pomoc i informacje")
        box.setIcon(QMessageBox.Icon.Information)
        box.setTextFormat(Qt.TextFormat.RichText)
        box.setText(text)

        logo_path = (
            Path(__file__).resolve().parent
            / "icons"
            / "quickbdot_logo.png"
        )
        if logo_path.is_file():
            box.setWindowIcon(QIcon(str(logo_path)))

        box.exec()

    def _reset_after_success(self):
        """Przywraca interfejs do stanu początkowego po udanym pobraniu."""
        try:
            self.admin_selector.clear_selection()
        except Exception:
            pass

        try:
            self.admin_selector.stop_selection(remove_layer=True)
        except Exception:
            pass

        self.extent_radio.setChecked(True)
        self.gpkg_radio.setChecked(True)
        self.apply_styles_checkbox.setChecked(True)

        self.output_path.clear()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.status.setText("")
        self.status.setVisible(False)
        self.download_btn.setEnabled(True)
        self.download_btn.setText("Pobierz i zapisz")

        self._build_bdot_tree()
        self._update_tree_height()
        self.refresh_vector_layers()
        self.update_area_mode()
        self.update_output_mode()

    def refresh_vector_layers(self):
        current_id = self.vector_layer_combo.currentData()

        self.vector_layer_combo.clear()

        for layer in QgsProject.instance().mapLayers().values():
            if not isinstance(layer, QgsVectorLayer):
                continue

            if not layer.isValid():
                continue

            geometry_type = QgsWkbTypes.geometryType(
                layer.wkbType()
            )

            if geometry_type != QgsWkbTypes.GeometryType.PolygonGeometry:
                continue

            self.vector_layer_combo.addItem(
                layer.name(),
                layer.id(),
            )

        if current_id:
            index = self.vector_layer_combo.findData(
                current_id
            )
            if index >= 0:
                self.vector_layer_combo.setCurrentIndex(index)

    def update_area_mode(self):
        vector_mode = self.vector_radio.isChecked()
        county_mode = self.county_radio.isChecked()

        self.vector_layer_combo.setEnabled(vector_mode)
        self.show_admin_btn.setEnabled(county_mode)
        self.clear_admin_btn.setEnabled(county_mode)

        if self.extent_radio.isChecked():
            self.admin_selector.stop_selection(
                remove_layer=True
            )
            self.admin_selection_label.setText(
                "Obszar: bieżący zasięg mapy."
            )
            self.download_btn.setText(
                "Pobierz i zapisz"
            )

        elif vector_mode:
            self.admin_selector.stop_selection(
                remove_layer=True
            )
            self.refresh_vector_layers()
            self.admin_selection_label.setText(
                "Obszar: geometria wskazanej warstwy poligonowej."
            )
            self.download_btn.setText(
                "Pobierz i zapisz"
            )

        else:
            self.admin_selection_label.setText(
                "Obszar: nie wybrano żadnego powiatu."
            )
            self.download_btn.setText(
                "Pobierz zaznaczone"
            )

    def show_admin_areas(self):
        try:
            self.status.setText(
                "Pobieram granice powiatów PRG z Geoportalu..."
            )
            QApplication.processEvents()

            layer = self.admin_selector.show_counties()

            self.iface.setActiveLayer(layer)

            self.status.setText(
                "Klikaj powiaty na mapie, aby je zaznaczać "
                "lub odznaczać."
            )

        except Exception as error:
            self.status.setVisible(True)
            self.status.setText("Błąd")
            self.result_details.setPlainText(
                "Błąd:\n" + str(error)
            )
            self.result_details.setVisible(True)

            QMessageBox.critical(
                self,
                "QuickBDOT – błąd",
                str(error),
            )

    def update_admin_selection_label(self, selected):
        count = len(selected or [])
        if count:
            self.county_radio.setText(
                f"Powiaty – wybór przestrzenny na mapie [{count}]"
            )
        else:
            self.county_radio.setText(
                "Powiaty – wybór na mapie"
            )

    def selected_vector_layer(self):
        layer_id = self.vector_layer_combo.currentData()

        if not layer_id:
            return None

        return QgsProject.instance().mapLayer(
            layer_id
        )

    def make_vector_mask_2180(self):
        source = self.selected_vector_layer()

        if source is None or not source.isValid():
            raise RuntimeError(
                "Nie wybrano poprawnej warstwy wektorowej."
            )

        if source.featureCount() == 0:
            raise RuntimeError(
                "Wybrana warstwa wektorowa nie zawiera obiektów."
            )

        mask = QgsVectorLayer(
            "MultiPolygon?crs=EPSG:2180",
            "QuickBDOT_vector_mask",
            "memory",
        )

        provider = mask.dataProvider()

        transform = QgsCoordinateTransform(
            source.crs(),
            QgsCoordinateReferenceSystem("EPSG:2180"),
            QgsProject.instance(),
        )

        geometries = []

        for feature in source.getFeatures():
            geometry = QgsGeometry(feature.geometry())

            if geometry.isNull() or geometry.isEmpty():
                continue

            if source.crs() != QgsCoordinateReferenceSystem("EPSG:2180"):
                geometry.transform(transform)

            geometries.append(geometry)

        if not geometries:
            raise RuntimeError(
                "Nie znaleziono prawidłowej geometrii "
                "w wybranej warstwie."
            )

        combined = QgsGeometry.unaryUnion(
            geometries
        )

        feature = QgsFeature()
        feature.setGeometry(combined)
        provider.addFeature(feature)
        mask.updateExtents()

        return mask

    def make_extent_mask_2180(self):
        canvas = self.iface.mapCanvas()

        src_crs = (
            canvas
            .mapSettings()
            .destinationCrs()
        )

        dst_crs = QgsCoordinateReferenceSystem(
            "EPSG:2180"
        )

        transform = QgsCoordinateTransform(
            src_crs,
            dst_crs,
            QgsProject.instance(),
        )

        extent = canvas.extent()

        points = [
            transform.transform(
                extent.xMinimum(),
                extent.yMinimum(),
            ),
            transform.transform(
                extent.xMinimum(),
                extent.yMaximum(),
            ),
            transform.transform(
                extent.xMaximum(),
                extent.yMinimum(),
            ),
            transform.transform(
                extent.xMaximum(),
                extent.yMaximum(),
            ),
        ]

        xs = [point.x() for point in points]
        ys = [point.y() for point in points]

        rect = QgsRectangle(
            min(xs),
            min(ys),
            max(xs),
            max(ys),
        )

        mask = QgsVectorLayer(
            "Polygon?crs=EPSG:2180",
            "QuickBDOT_extent",
            "memory",
        )

        feature = QgsFeature()
        feature.setGeometry(
            QgsGeometry.fromRect(rect)
        )

        mask.dataProvider().addFeature(feature)
        mask.updateExtents()

        return mask

    # -------------------------------------------------
    # ZAPIS
    # -------------------------------------------------

    def _detect_output_format(self, text):
        value = (text or "").strip().lower()
        if value.endswith(".shp"):
            self.shp_radio.setChecked(True)
            self.output_hint.setText(
                "Shapefile: każda warstwa zostanie zapisana jako osobny plik SHP."
            )
        elif value.endswith(".gpkg"):
            self.gpkg_radio.setChecked(True)
            self.output_hint.setText(
                "GeoPackage: wszystkie warstwy zostaną zapisane w jednym pliku."
            )
        else:
            self.output_hint.setText(
                "Format zostanie rozpoznany po rozszerzeniu: .gpkg lub .shp."
            )

    def update_output_mode(self):
        self._detect_output_format(
            self.output_path.text()
        )

    def choose_output(self):
        path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Wybierz plik wyjściowy",
            "",
            "GeoPackage (*.gpkg);;Shapefile (*.shp)",
        )

        if not path:
            return

        if "shapefile" in (selected_filter or "").lower():
            if not path.lower().endswith(".shp"):
                path += ".shp"
            self.shp_radio.setChecked(True)
        else:
            if not path.lower().endswith(".gpkg"):
                path += ".gpkg"
            self.gpkg_radio.setChecked(True)

        self.output_path.setText(path)
        self._detect_output_format(path)

    def _set_all_tree_items(self, state):
        self._tree_updating = True
        try:
            for i in range(self.class_tree.topLevelItemCount()):
                top = self.class_tree.topLevelItem(i)
                top.setCheckState(0, state)
                self._set_descendants_state(top, state)
        finally:
            self._tree_updating = False

    def _select_all_tree(self):
        self._set_all_tree_items(Qt.CheckState.Checked)

    def _clear_tree_selection(self):
        self._set_all_tree_items(Qt.CheckState.Unchecked)

    def _expand_tree(self):
        """Rozwija wszystkie gałęzie drzewa i pozostawia widok od góry."""
        self.class_tree.expandAll()
        self._update_tree_height()
        self.class_tree.scrollToTop()

        try:
            self.scroll_area.ensureWidgetVisible(
                self.class_tree,
                0,
                0,
            )
        except Exception:
            pass

    def _collapse_tree(self):
        """Zamyka wszystkie gałęzie drzewa i pozostawia widok od góry."""
        self.class_tree.collapseAll()
        self._update_tree_height()
        self.class_tree.scrollToTop()
        self.class_tree.scrollToTop()

        try:
            self.scroll_area.ensureWidgetVisible(
                self.class_tree,
                0,
                0,
            )
        except Exception:
            pass
        self._update_tree_height()

    def _visible_tree_row_count(self):
        count = 0

        def visit(item):
            nonlocal count
            count += 1

            if item.isExpanded():
                for child_index in range(item.childCount()):
                    visit(item.child(child_index))

        for i in range(self.class_tree.topLevelItemCount()):
            visit(self.class_tree.topLevelItem(i))

        return count

    def _update_tree_height(self, *args):
        try:
            rows = max(1, self._visible_tree_row_count())
            row_height = max(18, self.class_tree.fontMetrics().height() + 4)
            header_height = max(20, self.class_tree.header().sizeHint().height())
            wanted = header_height + rows * row_height + 6
            self.class_tree.setFixedHeight(
                max(100, min(460, wanted))
            )
        except Exception:
            pass

    def _build_bdot_tree(self):
        self.class_tree.clear()

        for category_code, category in BDOT_TREE.items():
            top = QTreeWidgetItem([f"{category_code} — {category['name']}"])
            top.setFlags(top.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            top.setCheckState(0, Qt.CheckState.Unchecked)
            top.setData(0, Qt.ItemDataRole.UserRole, {
                "level": 1,
                "code": category_code,
            })
            self.class_tree.addTopLevelItem(top)

            for class_code, class_info in category["classes"].items():
                class_item = QTreeWidgetItem([
                    f"{class_code} — {class_info['name']}"
                ])
                class_item.setFlags(
                    class_item.flags() | Qt.ItemFlag.ItemIsUserCheckable
                )
                class_item.setCheckState(0, Qt.CheckState.Unchecked)
                class_item.setToolTip(0, class_info["source"] + "_*")
                class_item.setData(0, Qt.ItemDataRole.UserRole, {
                    "level": 2,
                    "code": class_code,
                    "source": class_info["source"],
                    "name": class_info["name"],
                })
                top.addChild(class_item)

                for object_code, object_name in class_info["objects"]:
                    object_item = QTreeWidgetItem([
                        f"{object_code} — {object_name}"
                    ])
                    object_item.setFlags(
                        object_item.flags() | Qt.ItemFlag.ItemIsUserCheckable
                    )
                    object_item.setCheckState(0, Qt.CheckState.Unchecked)
                    object_item.setData(0, Qt.ItemDataRole.UserRole, {
                        "level": 3,
                        "code": object_code,
                        "name": object_name,
                    })
                    class_item.addChild(object_item)

        # Zachowujemy dotychczasowy wygodny start: Drogi i Budynki.
        self._set_class_checked("SKDR", True)
        self._set_class_checked("BUBD", True)
        self.class_tree.collapseAll()

    def _set_class_checked(self, class_code, checked):
        target_state = (
            Qt.CheckState.Checked
            if checked
            else Qt.CheckState.Unchecked
        )

        self._tree_updating = True
        try:
            for i in range(self.class_tree.topLevelItemCount()):
                top = self.class_tree.topLevelItem(i)
                for j in range(top.childCount()):
                    item = top.child(j)
                    data = item.data(0, Qt.ItemDataRole.UserRole) or {}
                    if data.get("code") != class_code:
                        continue

                    item.setCheckState(0, target_state)
                    for k in range(item.childCount()):
                        item.child(k).setCheckState(0, target_state)
                    self._refresh_parent_state(item.parent())
                    return
        finally:
            self._tree_updating = False

    def _set_descendants_state(self, item, state):
        for i in range(item.childCount()):
            child = item.child(i)
            child.setCheckState(0, state)
            self._set_descendants_state(child, state)

    def _refresh_parent_state(self, parent):
        while parent is not None:
            states = [
                parent.child(i).checkState(0)
                for i in range(parent.childCount())
            ]

            if states and all(
                state == Qt.CheckState.Checked
                for state in states
            ):
                parent.setCheckState(0, Qt.CheckState.Checked)
            elif states and all(
                state == Qt.CheckState.Unchecked
                for state in states
            ):
                parent.setCheckState(0, Qt.CheckState.Unchecked)
            else:
                parent.setCheckState(0, Qt.CheckState.PartiallyChecked)

            parent = parent.parent()

    def _on_tree_item_changed(self, item, column):
        if self._tree_updating or column != 0:
            return

        self._tree_updating = True
        try:
            state = item.checkState(0)

            # Kliknięcie kategorii/klasy zaznacza lub odznacza wszystkie dzieci.
            if item.childCount() and state in (
                Qt.CheckState.Checked,
                Qt.CheckState.Unchecked,
            ):
                self._set_descendants_state(item, state)

            self._refresh_parent_state(item.parent())
        finally:
            self._tree_updating = False

    def selected_plan(self):
        """
        Zwraca plan pobrania:
        {
          'OT_SKJZ': {
              'class_code': 'SKJZ',
              'label': 'SKJZ — Jezdnia',
              'objects': None | {'SKJZ01', 'SKJZ02'}
          }
        }

        objects=None oznacza całą klasę poziomu 2.
        """
        plan = {}

        for i in range(self.class_tree.topLevelItemCount()):
            top = self.class_tree.topLevelItem(i)

            for j in range(top.childCount()):
                class_item = top.child(j)
                class_data = (
                    class_item.data(0, Qt.ItemDataRole.UserRole) or {}
                )
                source = class_data.get("source")

                if not source:
                    continue

                checked_objects = set()
                total_objects = class_item.childCount()

                for k in range(total_objects):
                    child = class_item.child(k)
                    if child.checkState(0) == Qt.CheckState.Checked:
                        child_data = (
                            child.data(0, Qt.ItemDataRole.UserRole) or {}
                        )
                        code = child_data.get("code")
                        if code:
                            checked_objects.add(code)

                if not checked_objects:
                    continue

                objects = (
                    None
                    if len(checked_objects) == total_objects
                    else checked_objects
                )

                plan[source] = {
                    "class_code": class_data.get("code"),
                    "label": (
                        f"{class_data.get('code')} — "
                        f"{class_data.get('name')}"
                    ),
                    "objects": objects,
                }

        return plan

    def selected_codes(self):
        return list(self.selected_plan().keys())

    def _filter_level3(self, layer, class_code, selected_objects):
        """Filtruje klasę poziomu 2 po polu x_kod (poziom 3)."""
        if not selected_objects:
            return layer

        field_names = [field.name() for field in layer.fields()]
        xkod_field = next(
            (name for name in field_names if name.lower() == "x_kod"),
            None,
        )

        if xkod_field is None:
            raise RuntimeError(
                f"Klasa {class_code} nie zawiera pola x_kod, więc nie mogę "
                "zastosować wyboru poziomu 3. Zaznacz całą klasę poziomu 2."
            )

        wanted = {str(code).upper() for code in selected_objects}
        fids = []

        for feature in layer.getFeatures():
            value = feature[xkod_field]
            if value is None:
                continue
            if str(value).strip().upper() in wanted:
                fids.append(feature.id())

        if not fids:
            # Prawidłowy pusty wynik — może po prostu nie być wybranego typu
            # na danym obszarze. Tworzymy pustą warstwę o tym samym schemacie.
            geometry_name = QgsWkbTypes.displayString(layer.wkbType())
            crs_authid = layer.crs().authid() or "EPSG:2180"
            empty = QgsVectorLayer(
                f"{geometry_name}?crs={crs_authid}",
                layer.name(),
                "memory",
            )
            provider = empty.dataProvider()
            provider.addAttributes(layer.fields())
            empty.updateFields()
            return empty

        request = QgsFeatureRequest()
        request.setFilterFids(fids)
        filtered = layer.materialize(request)

        if not filtered.isValid():
            raise RuntimeError(
                f"Nie udało się odfiltrować poziomu 3 dla klasy {class_code}."
            )

        return filtered

    def set_progress(self, value):
        self.progress.setValue(value)
        self.progress.setVisible(True)
        QApplication.processEvents()

    def _layer_display_priority(self, layer, layer_name):
        """Zwraca priorytet rysowania. Wyższy = wyżej w panelu QGIS."""
        class_code = layer_name.split("—", 1)[0].strip().split(" ", 1)[0].upper()

        class_priority = {
            "PTTR": 100, "PTGN": 105, "PTNZ": 110, "PTKM": 115,
            "PTSO": 120, "PTWZ": 125, "PTUT": 130, "PTRK": 135,
            "PTLZ": 140, "PTZB": 150, "PTPL": 155,

            "KUMN": 180, "KUPG": 185, "KUHU": 190, "KUKO": 195,
            "KUSK": 200, "KUHO": 205, "KUOS": 210, "KUOZ": 215,
            "KUZA": 220, "KUSC": 225, "KUIK": 230,

            "TCON": 240, "TCPK": 245, "TCPN": 250, "TCRZ": 255,
            "ADJA": 260, "ADMS": 270,

            "PTWP": 340,

            "SWRM": 400, "SWKN": 410, "SWRS": 420,

            "SUPR": 500, "SULN": 510,

            "SKPP": 600, "SKRP": 610, "SKTR": 620,
            "SKDR": 630, "SKJZ": 640, "SKRW": 650,

            "BUZM": 700, "BUUO": 710, "BUHD": 720, "BUIN": 730,
            "BUSP": 740, "BUZT": 750, "BUTR": 760, "BUWT": 770,
            "BUIT": 780, "BUCM": 790, "BUIB": 800, "BUBD": 810,

            "OIMK": 850, "OISZ": 855, "OIPR": 900,
            "OIKM": 920, "OIOR": 940,
        }

        category_priority = {
            "PT": 100, "KU": 180, "TC": 240, "AD": 260,
            "SW": 400, "SU": 500, "SK": 600, "BU": 700, "OI": 850,
        }

        priority = class_priority.get(
            class_code,
            category_priority.get(class_code[:2], 300),
        )

        geometry_type = QgsWkbTypes.geometryType(layer.wkbType())

        if geometry_type == QgsWkbTypes.GeometryType.PointGeometry:
            priority += 30
        elif geometry_type == QgsWkbTypes.GeometryType.LineGeometry:
            priority += 20

        return int(priority)

    def _add_layer_ordered(
        self,
        saved_layer,
        layer_name,
        priority_override=None,
        visible=True,
    ):
        """Dodaje warstwę do grupy QuickBDOT w kolejności kartograficznej."""
        project = QgsProject.instance()
        root = project.layerTreeRoot()

        group_name = "QuickBDOT — BDOT10k"
        group = root.findGroup(group_name)

        if group is None:
            group = root.insertGroup(0, group_name)

        priority = (
            int(priority_override)
            if priority_override is not None
            else self._layer_display_priority(saved_layer, layer_name)
        )

        project.addMapLayer(saved_layer, False)

        insert_index = 0

        for index, child in enumerate(group.children()):
            child_priority = child.customProperty(
                "quickbdot_priority",
                -999999,
            )

            try:
                child_priority = int(child_priority)
            except Exception:
                child_priority = -999999

            if priority <= child_priority:
                insert_index = index + 1
            else:
                break

        node = group.insertLayer(insert_index, saved_layer)
        node.setCustomProperty("quickbdot_priority", priority)
        node.setItemVisibilityChecked(bool(visible))
        return node

    def _first_existing_field(self, layer, candidates):
        """
        Zwraca pierwsze istniejące pole.
        Obsługuje także nazwy z prefiksami GML, np.
        PL.PZGiK....__OT_Ulica_nazwa1.
        """
        fields = [field.name() for field in layer.fields()]
        field_map = {name.lower(): name for name in fields}

        # 1. dokładne dopasowanie
        for candidate in candidates:
            real = field_map.get(candidate.lower())
            if real:
                return real

        # 2. dopasowanie po końcówce
        for candidate in candidates:
            wanted = candidate.lower()
            for name in fields:
                low = name.lower()
                if low.endswith(wanted):
                    return name

        # 3. luźniejsze dopasowanie bez znaków _ i spacji
        def normalized(value):
            return re.sub(r"[^a-z0-9]+", "", value.lower())

        for candidate in candidates:
            wanted = normalized(candidate)
            for name in fields:
                if normalized(name).endswith(wanted):
                    return name

        return None

    def _field_has_values(self, layer, field_name, limit=300):
        """Sprawdza na próbce, czy pole zawiera jakąkolwiek niepustą wartość."""
        if not field_name:
            return False

        index = layer.fields().indexOf(field_name)
        if index < 0:
            return False

        checked = 0
        for feature in layer.getFeatures():
            value = feature[index]
            checked += 1

            if value is not None:
                text = str(value).strip()
                if text and text.lower() not in ("null", "none", "[]"):
                    return True

            if checked >= limit:
                break

        return False

    def _first_populated_field(self, layer, candidates):
        """
        Najpierw znajduje pole po nazwie, a następnie sprawdza,
        czy rzeczywiście zawiera dane.
        """
        checked_names = set()

        for candidate in candidates:
            field_name = self._first_existing_field(layer, [candidate])

            if not field_name or field_name in checked_names:
                continue

            checked_names.add(field_name)

            if self._field_has_values(layer, field_name):
                return field_name

        return None

    def _quoted_field(self, field_name):
        return '"' + str(field_name).replace('"', '""') + '"'

    def _name_expression(self, layer):
        field_name = self._first_existing_field(
            layer,
            ["nazwa", "NAZWA", "name"],
        )
        if not field_name:
            return None
        return self._quoted_field(field_name)

    def _street_expression(self, layer):
        """
        Nazwa ulicy. W aktualnych danych QuickBDOT pola występują m.in. jako:
        ULI_CECHA, ULI_NAZW_1, ULI_NAZW_2.
        """
        n1 = self._first_populated_field(
            layer,
            [
                "ULI_NAZW_1",
                "ULI_NAZWA1",
                "ulicaNazwa1",
                "OT_Ulica_nazwa1",
                "ul_nazwa1",
                "nazwa1",
            ],
        )
        n2 = self._first_populated_field(
            layer,
            [
                "ULI_NAZW_2",
                "ULI_NAZWA2",
                "ulicaNazwa2",
                "OT_Ulica_nazwa2",
                "ul_nazwa2",
                "nazwa2",
            ],
        )
        cecha = self._first_populated_field(
            layer,
            [
                "ULI_CECHA",
                "ulicaCecha",
                "ulica_cecha",
            ],
        )

        if not n1 and not n2:
            fallback = self._first_populated_field(
                layer,
                [
                    "NAZWA_UL",
                    "NAZWA_ULIC",
                    "nazwaUlicy",
                    "nazwaDrogi",
                    "ulica",
                    "nazwa",
                    "name",
                ],
            )
            return self._quoted_field(fallback) if fallback else None

        parts = []

        # Dla przykładu Żółkiewskiego + Stanisława -> Stanisława Żółkiewskiego
        if n2:
            parts.append(f"coalesce({self._quoted_field(n2)}, '')")

        if n1:
            parts.append(f"coalesce({self._quoted_field(n1)}, '')")

        name_expr = "trim(" + " || ' ' || ".join(parts) + ")"

        # Dodajemy skrót typu ulicy tylko gdy jest wypełniony.
        # Nie dodajemy go, jeśli byłby pusty/null.
        if cecha:
            cecha_q = self._quoted_field(cecha)
            return (
                "trim("
                f"CASE WHEN coalesce({cecha_q}, '') <> '' "
                f"THEN {cecha_q} || ' ' ELSE '' END || "
                f"{name_expr}"
                ")"
            )

        return name_expr

    def _road_number_expression(self, layer):
        """
        Wybiera pole zawierające PUBLICZNY numer drogi, a nie identyfikator
        odcinka typu 102724E.

        Akceptowane przykłady:
        92, 703, A2, S8, S17, DK92, DW702.
        """
        candidates = [
            "NAZWA_DROG",
            "NUMER_DROG",
            "NUMER_DROGI",
            "NUM_DROGI",
            "NR_DROGI",
            "numerDrogi",
            "nrDrogi",
            "numer_drogi",
        ]

        best_field = None
        best_score = 0

        public_number_re = re.compile(
            r"^(?:A|S|DK|DW)?\s*\d{1,3}[A-Z]?$",
            re.IGNORECASE,
        )

        for candidate in candidates:
            field_name = self._first_existing_field(layer, [candidate])
            if not field_name:
                continue

            field_index = layer.fields().indexOf(field_name)
            if field_index < 0:
                continue

            score = 0
            checked = 0

            for feature in layer.getFeatures():
                value = feature[field_index]
                checked += 1

                if value is not None:
                    text = str(value).strip()

                    if public_number_re.fullmatch(text):
                        score += 1

                if checked >= 500:
                    break

            if score > best_score:
                best_score = score
                best_field = field_name

        if not best_field or best_score == 0:
            return None

        q = self._quoted_field(best_field)

        # Odcinamy identyfikatory techniczne i przepuszczamy wyłącznie
        # krótkie numery dróg.
        return (
            "CASE "
            f"WHEN regexp_match(trim(to_string({q})), "
            "'^(A|S|DK|DW)?[ ]*[0-9]{1,3}[A-Z]?$') "
            f"THEN trim(to_string({q})) "
            "ELSE '' END"
        )

    def _configure_labeling(
        self,
        layer,
        expression,
        size_pt=9.0,
        bold=False,
        italic=False,
        color="#202020",
        buffer_mm=0.8,
        placement="point",
        repeat_distance=0,
    ):
        """Nadaje prostą, stabilną etykietę zgodną z API QGIS 4."""
        if not expression:
            return False

        settings = QgsPalLayerSettings()
        settings.enabled = True
        settings.fieldName = expression
        settings.isExpression = True
        settings.priority = 10

        try:
            settings.allowDegradedPlacement = True
        except Exception:
            pass

        try:
            settings.overlapHandling = Qgis.LabelOverlapHandling.AllowOverlapIfRequired
        except Exception:
            pass

        if placement == "line":
            try:
                settings.placement = Qgis.LabelPlacement.Curved
            except Exception:
                try:
                    settings.placement = Qgis.LabelPlacement.Line
                except Exception:
                    pass

            # Scalanie kolejnych odcinków o tej samej etykiecie ogranicza
            # powtarzanie nazwy na każdej pojedynczej geometrii.
            try:
                settings.mergeLines = True
            except Exception:
                pass

            try:
                settings.labelPerPart = False
            except Exception:
                pass

            settings.repeatDistance = float(repeat_distance or 0)

            try:
                settings.repeatDistanceUnit = Qgis.RenderUnit.MetersInMapUnits
            except Exception:
                pass
        else:
            try:
                settings.placement = Qgis.LabelPlacement.AroundPoint
            except Exception:
                pass
            settings.dist = 1.2

        text_format = QgsTextFormat()
        font = QFont("Arial")
        font.setBold(bool(bold))
        font.setItalic(bool(italic))
        text_format.setFont(font)
        text_format.setSize(float(size_pt))
        text_format.setColor(QColor(color))

        buffer = QgsTextBufferSettings()
        buffer.setEnabled(True)
        buffer.setSize(float(buffer_mm))
        buffer.setColor(QColor("#FFFFFF"))
        text_format.setBuffer(buffer)

        settings.setFormat(text_format)

        layer.setLabeling(
            QgsVectorLayerSimpleLabeling(settings)
        )
        layer.setLabelsEnabled(True)
        layer.triggerRepaint()
        return True

    def _add_programmatic_label_layer(
        self,
        source_layer,
        display_name,
        expression,
        priority,
        max_scale=15000,
        subset_expression=None,
        size_pt=9.0,
        bold=False,
        italic=False,
        color="#202020",
        placement="point",
        repeat_distance=0,
    ):
        """
        Tworzy warstwę tylko do etykietowania.
        Symbole są wyłączone, więc warstwa nie dubluje geometrii na mapie.
        """
        aux_layer = QgsVectorLayer(
            source_layer.source(),
            display_name,
            "ogr",
        )

        if not aux_layer.isValid():
            return False

        if subset_expression:
            aux_layer.setSubsetString(subset_expression)

        try:
            aux_layer.setRenderer(QgsNullSymbolRenderer())
        except Exception:
            pass

        if max_scale:
            try:
                aux_layer.setScaleBasedVisibility(True)
                aux_layer.setMinimumScale(float(max_scale))
                aux_layer.setMaximumScale(0.0)
            except Exception:
                pass

        if not self._configure_labeling(
            aux_layer,
            expression,
            size_pt=size_pt,
            bold=bold,
            italic=italic,
            color=color,
            placement=placement,
            repeat_distance=repeat_distance,
        ):
            return False

        self._add_layer_ordered(
            aux_layer,
            display_name,
            priority_override=priority,
            visible=True,
        )
        return True

    def _add_auxiliary_view_layer(
        self,
        source_layer,
        display_name,
        qml_name,
        priority,
        subset_expression=None,
        max_scale=None,
        visible=True,
    ):
        """
        Tworzy dodatkową warstwę widokową wskazującą na te same dane.
        Może mieć własny filtr, zakres skalowy i domyślną widoczność.
        """
        aux_layer = QgsVectorLayer(
            source_layer.source(),
            display_name,
            "ogr",
        )

        if not aux_layer.isValid():
            return False

        if subset_expression:
            aux_layer.setSubsetString(subset_expression)

        if not apply_auxiliary_qml(aux_layer, qml_name):
            return False

        if max_scale:
            try:
                # QGIS: minimumScale is the MOST ZOOMED-OUT boundary.
                # Example 50000 => visible at 1:10 000, hidden at 1:100 000.
                aux_layer.setScaleBasedVisibility(True)
                aux_layer.setMinimumScale(float(max_scale))
                aux_layer.setMaximumScale(0.0)
            except Exception:
                pass

        self._add_layer_ordered(
            aux_layer,
            display_name,
            priority_override=priority,
            visible=visible,
        )
        return True

    def _add_cartographic_overlays(self, saved_layer, class_code):
        """
        Etykiety przygotowane pod mapę topograficzną 1:10 000.

        ADMS:
        - etykiety są na GŁÓWNEJ warstwie punktowej,
        - symbol punktowy jest wyłączony,
        - brak filtrów x_kod, więc nie gubimy miejscowości.

        SKJZ:
        - nazwy ulic są bezpośrednio na głównej warstwie,
        - numery dróg są na dodatkowej niewidocznej symbolicznie warstwie.
        """
        code = (class_code or "").upper()
        geometry_type = QgsWkbTypes.geometryType(saved_layer.wkbType())

        # -----------------------------------------------------
        # ADMS — etykietowanie bezpośrednio na warstwie punktowej
        # -----------------------------------------------------
        if (
            code == "ADMS"
            and geometry_type == QgsWkbTypes.GeometryType.PointGeometry
        ):
            name_expr = self._name_expression(saved_layer)

            if name_expr:
                try:
                    # Punktów nie rysujemy, ale WARSTWA pozostaje włączona,
                    # aby QGIS mógł wyświetlać jej etykiety.
                    saved_layer.setRenderer(QgsNullSymbolRenderer())
                except Exception:
                    pass

                self._configure_labeling(
                    saved_layer,
                    name_expr,
                    size_pt=9.0,
                    bold=True,
                    color="#111111",
                    buffer_mm=0.9,
                    placement="point",
                )

                try:
                    saved_layer.setScaleBasedVisibility(True)
                    # Główne zastosowanie BDOT10k: okolice 1:10 000.
                    saved_layer.setMinimumScale(25000.0)
                    saved_layer.setMaximumScale(0.0)
                except Exception:
                    pass

            return

        # -----------------------------------------------------
        # SKJZ — osobne warstwy etykietowe dla ulic i numerów dróg
        # -----------------------------------------------------
        if (
            code == "SKJZ"
            and geometry_type == QgsWkbTypes.GeometryType.LineGeometry
        ):
            # Dodatkowe reprezentacje kartograficzne dróg pozostają.
            road_overlays = [
                (
                    "SKJZ — dodatkowa symbolizacja dróg",
                    "OT_SKJZ_L [33-38].qml",
                    720,
                ),
                (
                    "SKJZ — odcinki nad gruntem",
                    "OT_SKJZ_L nad gruntem [47].qml",
                    730,
                ),
                (
                    "SKJZ — odcinki pod gruntem",
                    "OT_SKJZ_L pod gruntem [20].qml",
                    710,
                ),
            ]

            for display_name, qml_name, priority in road_overlays:
                try:
                    self._add_auxiliary_view_layer(
                        saved_layer,
                        display_name,
                        qml_name,
                        priority,
                        max_scale=None,
                    )
                except Exception:
                    pass

            # Nazwy ulic: osobna warstwa, bez symbolu geometrycznego.
            street_expr = self._street_expression(saved_layer)

            try:
                saved_layer.setCustomProperty(
                    "quickbdot_street_expression",
                    street_expr or "",
                )
            except Exception:
                pass

            if street_expr:
                try:
                    self._add_programmatic_label_layer(
                        saved_layer,
                        "SKJZ — nazwy ulic",
                        street_expr,
                        1400,
                        max_scale=20000,
                        size_pt=8.0,
                        bold=False,
                        color="#242424",
                        placement="line",
                        repeat_distance=350,
                    )
                except Exception:
                    pass
            else:
                field_names = ", ".join(
                    field.name()
                    for field in saved_layer.fields()
                )
                self.status.setText(
                    "Brak wypełnionego pola nazwy ulicy w SKJZ. "
                    "Dostępne pola: " + field_names
                )

            # Numery dróg: druga osobna warstwa etykietowa.
            road_number_expr = self._road_number_expression(saved_layer)

            try:
                saved_layer.setCustomProperty(
                    "quickbdot_road_number_expression",
                    road_number_expr or "",
                )
            except Exception:
                pass

            if road_number_expr:
                try:
                    self._add_programmatic_label_layer(
                        saved_layer,
                        "SKJZ — numery dróg",
                        road_number_expr,
                        1410,
                        max_scale=25000,
                        size_pt=8.5,
                        bold=True,
                        color="#111111",
                        placement="line",
                        repeat_distance=1200,
                    )
                except Exception:
                    pass

            return

        # -----------------------------------------------------
        # SWRS — nazwy rzek
        # -----------------------------------------------------
        if (
            code == "SWRS"
            and geometry_type == QgsWkbTypes.GeometryType.LineGeometry
        ):
            name_expr = self._name_expression(saved_layer)

            if name_expr:
                self._configure_labeling(
                    saved_layer,
                    name_expr,
                    size_pt=8.0,
                    italic=True,
                    color="#1E78B4",
                    buffer_mm=0.6,
                    placement="line",
                )

                try:
                    saved_layer.setScaleBasedVisibility(True)
                    saved_layer.setMinimumScale(25000.0)
                    saved_layer.setMaximumScale(0.0)
                except Exception:
                    pass

            return

        # -----------------------------------------------------
        # SKTR — dodatkowe reprezentacje kolei
        # -----------------------------------------------------
        if (
            code == "SKTR"
            and geometry_type == QgsWkbTypes.GeometryType.LineGeometry
        ):
            rail_overlays = [
                (
                    "SKTR — tory nad gruntem",
                    "OT_SKTR_L nad gruntem [47].qml",
                    700,
                ),
                (
                    "SKTR — tory pod gruntem",
                    "OT_SKTR_L pod gruntem [20].qml",
                    690,
                ),
            ]

            for display_name, qml_name, priority in rail_overlays:
                try:
                    self._add_auxiliary_view_layer(
                        saved_layer,
                        display_name,
                        qml_name,
                        priority,
                        max_scale=None,
                    )
                except Exception:
                    pass

    def _normalized_output_path(self):
        raw = self.output_path.text().strip()
        if not raw:
            return ""

        path = Path(raw)
        suffix = path.suffix.lower()

        if suffix == ".shp":
            self.shp_radio.setChecked(True)
            return str(path)

        if suffix == ".gpkg":
            self.gpkg_radio.setChecked(True)
            return str(path)

        path = Path(str(path) + ".gpkg")
        self.gpkg_radio.setChecked(True)
        self.output_path.setText(str(path))
        return str(path)


    def _shapefile_safe_layer(self, layer):
        """Return a memory copy with straight, basic geometries for ESRI Shapefile.

        BDOT10k GML may contain curve-based OGC geometries (e.g. MultiCurve /
        CurvePolygon). GeoPackage accepts them, while the ESRI Shapefile driver
        only supports basic point/line/polygon geometries.
        """
        geom_type = QgsWkbTypes.geometryType(layer.wkbType())
        if geom_type == QgsWkbTypes.GeometryType.PointGeometry:
            memory_geom = "MultiPoint"
        elif geom_type == QgsWkbTypes.GeometryType.LineGeometry:
            memory_geom = "MultiLineString"
        elif geom_type == QgsWkbTypes.GeometryType.PolygonGeometry:
            memory_geom = "MultiPolygon"
        else:
            raise RuntimeError(
                f"Nieobsługiwany typ geometrii dla Shapefile: {layer.wkbType()}"
            )

        source_crs = layer.crs()
        crs_authid = source_crs.authid() if source_crs.isValid() else "EPSG:2180"
        uri = f"{memory_geom}?crs={crs_authid}"

        safe = QgsVectorLayer(uri, "QuickBDOT_SHP_TEMP", "memory")
        if not safe.isValid():
            raise RuntimeError("Nie udało się utworzyć warstwy tymczasowej SHP.")

        provider = safe.dataProvider()
        provider.addAttributes(list(layer.fields()))
        safe.updateFields()

        out_features = []
        for src in layer.getFeatures():
            dst = QgsFeature(safe.fields())
            dst.setAttributes(src.attributes())

            geom = QgsGeometry(src.geometry())
            if not geom.isNull():
                try:
                    # Shapefile does not support circular/curve geometries.
                    geom.convertToStraightSegment()
                except Exception:
                    pass
                try:
                    geom.convertToMultiType()
                except Exception:
                    pass
                dst.setGeometry(geom)

            out_features.append(dst)

        ok, _ = provider.addFeatures(out_features)
        safe.updateExtents()
        if not ok:
            raise RuntimeError(
                "Nie udało się przygotować geometrii do zapisu Shapefile."
            )
        return safe


    def _prepare_shapefile_for_overwrite(self, shp_path):
        """Release and remove an existing Shapefile set before overwrite.

        On Windows an already loaded OGR layer can keep SHP/DBF/SHX files
        open. QgsVectorFileWriter then tries to recreate the datasource and
        GDAL may report misleading errors such as "...shp is not a directory".
        """
        shp_path = Path(shp_path)
        target = str(shp_path.resolve()).lower()
        project = QgsProject.instance()

        # Remove project layers which point to the same physical Shapefile.
        # OGR source strings may include provider options after a pipe.
        to_remove = []
        for map_layer in project.mapLayers().values():
            try:
                source = (map_layer.source() or "").split("|", 1)[0]
                if not source:
                    continue
                source_path = str(Path(source).resolve()).lower()
                if source_path == target:
                    to_remove.append(map_layer.id())
            except Exception:
                continue

        if to_remove:
            project.removeMapLayers(to_remove)
            QApplication.processEvents()

        # Delete the whole Shapefile family. A single layer consists of many
        # sidecar files, and leaving one stale/locked file can break creation.
        suffixes = [
            ".shp", ".shx", ".dbf", ".prj", ".qpj", ".cpg",
            ".sbn", ".sbx", ".qix", ".fix", ".shp.xml",
        ]
        blocked = []
        base = shp_path.with_suffix("")
        for suffix in suffixes:
            candidate = Path(str(base) + suffix)
            if not candidate.exists():
                continue
            try:
                candidate.unlink()
            except Exception as exc:
                blocked.append(f"{candidate.name}: {exc}")

        if blocked:
            raise RuntimeError(
                "Nie można nadpisać istniejącego Shapefile, ponieważ część "
                "plików jest nadal używana lub zablokowana.\n\n"
                + "\n".join(blocked)
                + "\n\nUsuń/wyłącz warstwę z projektu lub wybierz inną nazwę pliku."
            )

        # Ensure the main target really disappeared before GDAL Create().
        if shp_path.exists():
            raise RuntimeError(
                f"Nie udało się usunąć starego pliku przed zapisem:\n{shp_path}"
            )

    def save_layer(self, layer, layer_name):
        output = self._normalized_output_path()

        if not output:
            raise RuntimeError(
                "Nie wybrano miejsca zapisu."
            )

        context = QgsProject.instance().transformContext()

        # Format zapisu ustalamy wyłącznie po rozszerzeniu ścieżki.
        # Ukryte QRadioButton nie są wiarygodnym źródłem stanu, ponieważ
        # nie należą do wspólnej grupy i oba mogą pozostać zaznaczone.
        output_suffix = Path(output).suffix.lower()

        if output_suffix == ".gpkg":
            options = QgsVectorFileWriter.SaveVectorOptions()
            options.driverName = "GPKG"
            options.layerName = layer_name
            options.fileEncoding = "UTF-8"

            if Path(output).exists():
                options.actionOnExistingFile = (
                    QgsVectorFileWriter.ActionOnExistingFile
                    .CreateOrOverwriteLayer
                )
            else:
                options.actionOnExistingFile = (
                    QgsVectorFileWriter.ActionOnExistingFile
                    .CreateOrOverwriteFile
                )

            result = QgsVectorFileWriter.writeAsVectorFormatV3(
                layer,
                output,
                context,
                options,
            )

            if result[0] != QgsVectorFileWriter.WriterError.NoError:
                raise RuntimeError(
                    f"Błąd zapisu warstwy {layer_name}:\n{result}"
                )

            saved_source = f"{output}|layername={layer_name}"
            saved_layer = QgsVectorLayer(
                saved_source,
                layer_name,
                "ogr",
            )

        elif output_suffix == ".shp":
            output_path = Path(output)

            # Przy zapisie SHP użytkownik wskazuje plik bazowy, np.
            # C:/Dane/bdot.shp. Każda klasa BDOT10k musi jednak trafić
            # do osobnego zestawu plików Shapefile, dlatego tworzymy:
            # bdot_SWRS.shp, bdot_SKJZ.shp itd.
            if output_path.suffix.lower() == ".shp":
                folder = output_path.parent
                base_name = output_path.stem
            else:
                folder = output_path
                base_name = "QuickBDOT"

            folder.mkdir(
                parents=True,
                exist_ok=True,
            )

            class_code = (
                layer_name
                .split("—", 1)[0]
                .strip()
                .split(" ", 1)[0]
                .upper()
            )

            # Nazwy fizycznych plików pozostają krótkie i bezpieczne
            # dla GDAL/OGR, natomiast pełna nazwa warstwy jest zachowana
            # w panelu QGIS.
            safe_code = "".join(
                ch for ch in class_code
                if ch.isalnum() or ch in ("_", "-")
            ) or "WARSTWA"
            safe_base = "".join(
                ch for ch in base_name
                if ch.isalnum() or ch in ("_", "-")
            ) or "QuickBDOT"

            shp_path = folder / f"{safe_base}_{safe_code}.shp"

            # Nie nadpisujemy istniejącego zestawu SHP. QGIS/GDAL na Windows
            # może nadal trzymać uchwyty do .shp/.dbf/.shx, nawet po usunięciu
            # warstwy z projektu. Zamiast ryzykować błąd WinError 32 wybieramy
            # automatycznie kolejną wolną nazwę: _2, _3, ...
            def _shp_family_exists(path):
                base = path.with_suffix("")
                suffixes = (
                    ".shp", ".shx", ".dbf", ".prj", ".qpj", ".cpg",
                    ".sbn", ".sbx", ".qix", ".fix", ".shp.xml",
                )
                return any(Path(str(base) + suffix).exists() for suffix in suffixes)

            if _shp_family_exists(shp_path):
                counter = 2
                while True:
                    candidate = folder / f"{safe_base}_{safe_code}_{counter}.shp"
                    if not _shp_family_exists(candidate):
                        shp_path = candidate
                        break
                    counter += 1

            options = QgsVectorFileWriter.SaveVectorOptions()
            options.driverName = "ESRI Shapefile"
            options.fileEncoding = "UTF-8"
            options.actionOnExistingFile = (
                QgsVectorFileWriter.ActionOnExistingFile
                .CreateOrOverwriteFile
            )

            # BDOT10k GML can use curve geometries unsupported by SHP.
            # Linearize them and force basic multipart geometry before export.
            export_layer = self._shapefile_safe_layer(layer)

            result = QgsVectorFileWriter.writeAsVectorFormatV3(
                export_layer,
                str(shp_path),
                context,
                options,
            )

            if result[0] != QgsVectorFileWriter.WriterError.NoError:
                raise RuntimeError(
                    f"Błąd zapisu warstwy {layer_name}:\n{result}"
                )

            # writeAsVectorFormatV3 może zwrócić faktycznie utworzoną
            # ścieżkę w trzecim elemencie wyniku. Używamy jej, jeśli
            # jest dostępna, a w przeciwnym razie ścieżki żądanej.
            actual_path = str(shp_path)
            if len(result) > 2 and result[2]:
                candidate = str(result[2])
                if Path(candidate).exists():
                    actual_path = candidate

            if not Path(actual_path).exists():
                raise RuntimeError(
                    f"Warstwa {layer_name} została zgłoszona jako zapisana, "
                    "ale plik SHP nie istnieje.\n\n"
                    f"Oczekiwany plik: {shp_path}"
                )

            saved_source = actual_path
            saved_layer = QgsVectorLayer(
                saved_source,
                layer_name,
                "ogr",
            )

        else:
            raise RuntimeError(
                f"Nieobsługiwany format wyjściowy: {output_suffix or '(brak rozszerzenia)'}. "
                "Wybierz plik .gpkg lub .shp."
            )

        if not saved_layer.isValid():
            raise RuntimeError(
                f"Warstwa {layer_name} została zapisana, ale QGIS nie może jej otworzyć.\n\n"
                f"Źródło: {saved_source}\n"
                "Sprawdź, czy plik istnieje, nie jest zablokowany przez inną aplikację "
                "i czy GDAL/OGR może go odczytać."
            )

        class_code = (
            layer_name
            .split("—", 1)[0]
            .strip()
            .split(" ", 1)[0]
            .upper()
        )

        if self.apply_styles_checkbox.isChecked():
            try:
                apply_bdot_style(
                    saved_layer,
                    class_code,
                )
            except Exception:
                # Styl nie może zatrzymać pobierania danych.
                pass

        geometry_type = QgsWkbTypes.geometryType(saved_layer.wkbType())

        main_visible = True

        # Ronda/węzły oraz punktowa reprezentacja ADMS mają być
        # dodane do projektu, ale domyślnie wyłączone.
        if self.apply_styles_checkbox.isChecked():
            if class_code == "SKRW":
                main_visible = False

            if (
                class_code == "ADMS"
                and geometry_type == QgsWkbTypes.GeometryType.PointGeometry
            ):
                # Warstwa pozostaje włączona, bo służy do etykietowania.
                main_visible = True

            if (
                class_code == "KUPG"
                and geometry_type == QgsWkbTypes.GeometryType.PointGeometry
            ):
                main_visible = False

        self._add_layer_ordered(
            saved_layer,
            layer_name,
            visible=main_visible,
        )

        if self.apply_styles_checkbox.isChecked():
            self._add_cartographic_overlays(
                saved_layer,
                class_code,
            )

    # -------------------------------------------------
    # POBIERANIE
    # -------------------------------------------------

    def _mask_geometry(self, mask_layer):
        """Scala geometrię maski do jednej geometrii."""
        geometries = []

        for feature in mask_layer.getFeatures():
            geometry = QgsGeometry(feature.geometry())

            if geometry.isNull() or geometry.isEmpty():
                continue

            geometries.append(geometry)

        if not geometries:
            raise RuntimeError(
                "Maska obszaru nie zawiera prawidłowej geometrii."
            )

        if len(geometries) == 1:
            return geometries[0]

        return QgsGeometry.unaryUnion(geometries)

    def _download_zip_inline(self, url):
        """
        Pobiera archiwum bez osobnego okna postępu.
        Postęp jest prezentowany wyłącznie przez pasek w interfejsie QuickBDOT.
        """
        temp_file = tempfile.NamedTemporaryFile(
            prefix="quickbdot_",
            suffix=".zip",
            delete=False,
        )
        temp_path = temp_file.name
        temp_file.close()

        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "QuickBDOT/0.0.37 QGIS",
            },
        )

        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                total_header = response.headers.get("Content-Length")
                try:
                    total = int(total_header) if total_header else 0
                except (TypeError, ValueError):
                    total = 0

                downloaded = 0
                chunk_size = 1024 * 256

                with open(temp_path, "wb") as target:
                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break

                        target.write(chunk)
                        downloaded += len(chunk)

                        if total > 0:
                            percent = int(
                                min(100, downloaded * 100 / total)
                            )
                            self.set_progress(percent)
                        else:
                            # Gdy serwer nie podaje rozmiaru, pasek pozostaje
                            # aktywny i pokazuje orientacyjny postęp pobierania.
                            self.progress.setRange(0, 0)

                        QApplication.processEvents()

                self.progress.setRange(0, 100)
                self.progress.setValue(100)
                QApplication.processEvents()

            return temp_path

        except Exception:
            self.progress.setRange(0, 100)
            self.progress.setValue(0)

            try:
                Path(temp_path).unlink(missing_ok=True)
            except Exception:
                pass

            raise

    def _repair_invalid_geometries(self, layer):
        """
        Tworzy kopię warstwy z naprawionymi geometriami.
        Chroni operację przycinania przed błędem pojedynczych obiektów
        BDOT10k o niepoprawnej geometrii.
        """
        geometry_name = QgsWkbTypes.displayString(layer.wkbType())
        crs_authid = layer.crs().authid() or "EPSG:2180"

        repaired = QgsVectorLayer(
            f"{geometry_name}?crs={crs_authid}",
            layer.name() + "_repaired",
            "memory",
        )

        provider = repaired.dataProvider()
        provider.addAttributes(layer.fields())
        repaired.updateFields()

        output_features = []

        for source_feature in layer.getFeatures():
            new_feature = QgsFeature(repaired.fields())
            new_feature.setAttributes(source_feature.attributes())

            geometry = source_feature.geometry()

            if geometry is None or geometry.isNull() or geometry.isEmpty():
                continue

            try:
                if not geometry.isGeosValid():
                    fixed = geometry.makeValid()

                    if (
                        fixed is None
                        or fixed.isNull()
                        or fixed.isEmpty()
                    ):
                        continue

                    geometry = fixed
            except Exception:
                try:
                    geometry = geometry.makeValid()
                except Exception:
                    continue

            # makeValid może zwrócić kolekcję zawierającą elementy
            # o innym typie; odrzucamy wynik, jeśli nie odpowiada
            # podstawowemu typowi geometrii źródłowej.
            try:
                source_geom_type = QgsWkbTypes.geometryType(
                    layer.wkbType()
                )
                fixed_geom_type = QgsWkbTypes.geometryType(
                    geometry.wkbType()
                )

                if fixed_geom_type != source_geom_type:
                    continue
            except Exception:
                pass

            new_feature.setGeometry(geometry)
            output_features.append(new_feature)

        if output_features:
            provider.addFeatures(output_features)

        repaired.updateExtents()
        return repaired

    def _ensure_epsg2180(self, layer):
        """Return a layer whose geometry and CRS are explicitly EPSG:2180.

        County downloads can contain GML layers with CRS metadata which differs
        between packages/providers. When only one source layer is used, the old
        code skipped merge/reprojection and that source CRS leaked into SHP.
        This helper makes the county pipeline deterministic.
        """
        target_crs = QgsCoordinateReferenceSystem("EPSG:2180")
        source_crs = layer.crs()

        # If the source CRS is valid and genuinely different, transform the
        # coordinates. This is the safe case because QGIS knows both systems.
        if source_crs.isValid() and source_crs != target_crs:
            result = processing.run(
                "native:reprojectlayer",
                {
                    "INPUT": layer,
                    "TARGET_CRS": target_crs,
                    "OUTPUT": "TEMPORARY_OUTPUT",
                },
            )["OUTPUT"]
            result.setCrs(target_crs)
            return result

        # If the GML has no usable CRS metadata, BDOT10k county packages used
        # by this workflow are requested/handled in PL-1992. Preserve the
        # coordinates and assign the missing CRS explicitly.
        if not source_crs.isValid():
            detached = layer.materialize(QgsFeatureRequest())
            detached.setCrs(target_crs)
            return detached

        # Already EPSG:2180. Keep a detached copy so the CRS is explicit and
        # independent from temporary source files.
        detached = layer.materialize(QgsFeatureRequest())
        detached.setCrs(target_crs)
        return detached

    def _download_counties(self, plan, units, mask_layer=None):
        """Pobiera wskazane powiaty, scala klasy, filtruje poziom 3 i przycina."""
        codes = list(plan.keys())
        if not units:
            raise RuntimeError(
                "Nie znaleziono żadnego powiatu do pobrania."
            )

        collected = {code: [] for code in codes}
        missing = []
        seen_urls = set()
        total = len(units)

        for number, unit in enumerate(units, start=1):
            name = unit["name"]
            geometry = QgsGeometry(unit["geometry"])

            if geometry.isNull() or geometry.isEmpty():
                missing.append(f"{name} – brak geometrii")
                continue

            point_geom = geometry.pointOnSurface()
            point = point_geom.asPoint()
            rect = geometry.boundingBox()

            xmin = rect.xMinimum()
            ymin = rect.yMinimum()
            xmax = rect.xMaximum()
            ymax = rect.yMaximum()

            if xmax - xmin < 100:
                xmin = point.x() - 50
                xmax = point.x() + 50

            if ymax - ymin < 100:
                ymin = point.y() - 50
                ymax = point.y() + 50

            self.status.setText(
                f"[{number}/{total}] Szukam paczki: {name}..."
            )
            QApplication.processEvents()

            zip_url = get_county_zip_url(
                point.x(),
                point.y(),
                (xmin, ymin, xmax, ymax),
                "EPSG:2180",
            )

            if zip_url in seen_urls:
                continue

            seen_urls.add(zip_url)

            self.status.setText(
                f"[{number}/{total}] Pobieram: {name}..."
            )
            QApplication.processEvents()

            self.progress.setRange(0, 100)
            self.progress.setValue(0)

            zip_path = self._download_zip_inline(
                zip_url
            )

            self.status.setText(
                f"[{number}/{total}] Odczytuję klasy: {name}..."
            )
            QApplication.processEvents()

            found = extract_selected_classes(
                zip_path,
                codes,
            )

            for code in codes:
                paths = found.get(code, [])

                if not paths:
                    missing.append(f"{name} – {code}")
                    continue

                for path in paths:
                    source_layer = QgsVectorLayer(
                        path,
                        f"{code}_{number}",
                        "ogr",
                    )

                    if not source_layer.isValid():
                        missing.append(
                            f"{name} – {code}: QGIS nie otworzył źródła"
                        )
                        continue

                    # Odłączamy dane od plików w katalogu TEMP, ponieważ
                    # następny powiat nadpisze te pliki.
                    detached = source_layer.materialize(
                        QgsFeatureRequest()
                    )

                    if not detached.isValid():
                        missing.append(
                            f"{name} – {code}: nie udało się utworzyć kopii"
                        )
                        continue

                    detached = self._ensure_epsg2180(detached)
                    collected[code].append(detached)

        added = []

        for code, selection in plan.items():
            layers = collected.get(code, [])

            if not layers:
                continue

            label = selection["label"]
            class_code = selection["class_code"]
            selected_objects = selection["objects"]

            # Jedna klasa BDOT10k może występować w paczce w więcej niż
            # jednym typie geometrii (np. punkt/linia/poligon). QGIS nie
            # pozwala scalać różnych typów geometrii w jednej warstwie,
            # więc grupujemy je przed scaleniem.
            geometry_groups = {}

            for layer in layers:
                geometry_type = QgsWkbTypes.geometryType(layer.wkbType())
                geometry_groups.setdefault(geometry_type, []).append(layer)

            multiple_geometries = len(geometry_groups) > 1

            for geometry_type, geometry_layers in geometry_groups.items():
                if geometry_type == QgsWkbTypes.GeometryType.PointGeometry:
                    geometry_suffix = "P"
                    geometry_name = "punkt"
                elif geometry_type == QgsWkbTypes.GeometryType.LineGeometry:
                    geometry_suffix = "L"
                    geometry_name = "linia"
                elif geometry_type == QgsWkbTypes.GeometryType.PolygonGeometry:
                    geometry_suffix = "A"
                    geometry_name = "poligon"
                else:
                    geometry_suffix = "G"
                    geometry_name = "geometria"

                output_label = (
                    f"{label} [{geometry_suffix}]"
                    if multiple_geometries
                    else label
                )

                self.status.setText(
                    f"Scalam klasę: {output_label}..."
                )
                QApplication.processEvents()

                if len(geometry_layers) == 1:
                    result_layer = self._ensure_epsg2180(geometry_layers[0])
                else:
                    merge_result = processing.run(
                        "native:mergevectorlayers",
                        {
                            "LAYERS": geometry_layers,
                            "CRS": QgsCoordinateReferenceSystem("EPSG:2180"),
                            "OUTPUT": "TEMPORARY_OUTPUT",
                        },
                    )
                    result_layer = self._ensure_epsg2180(merge_result["OUTPUT"])

                # Jeżeli wybrano tylko część poziomu 3, filtrujemy po x_kod.
                if selected_objects is not None:
                    self.status.setText(
                        f"Filtruję poziom 3: {output_label}..."
                    )
                    QApplication.processEvents()
                    result_layer = self._filter_level3(
                        result_layer,
                        class_code,
                        selected_objects,
                    )

                # Dla aktualnego widoku i warstwy wektorowej przycinamy
                # dopiero PO scaleniu danych ze wszystkich przecinających powiatów.
                if mask_layer is not None:
                    self.status.setText(
                        f"Przycinam: {output_label}..."
                    )
                    QApplication.processEvents()

                    # Niektóre źródłowe obiekty BDOT10k mogą mieć
                    # niepoprawną geometrię. Naprawiamy je przed clipem,
                    # zamiast zatrzymywać cały proces na jednym obiekcie.
                    result_layer = self._repair_invalid_geometries(
                        result_layer
                    )

                    clip_result = processing.run(
                        "native:clip",
                        {
                            "INPUT": result_layer,
                            "OVERLAY": mask_layer,
                            "OUTPUT": "TEMPORARY_OUTPUT",
                        },
                    )

                    result_layer = clip_result["OUTPUT"]

                # Nie zapisuj pustych wyników po filtrze/przycięciu.
                if result_layer.featureCount() == 0:
                    missing.append(
                        f"{output_label}: brak obiektów po filtrze/przycięciu"
                    )
                    continue

                result_layer.setName(output_label)

                self.status.setText(
                    f"Zapisuję: {output_label}..."
                )
                QApplication.processEvents()

                self.save_layer(
                    result_layer,
                    output_label,
                )
                added.append(output_label)

        self.progress.setValue(100)

        if not added:
            raise RuntimeError(
                "Nie udało się utworzyć żadnej z wybranych klas."
            )

        message = (
            f"Gotowe.\n\nPobrano {len(seen_urls)} paczek powiatowych.\n\n"
            "Zapisano i dodano warstwy:\n• "
            + "\n• ".join(added)
        )

        if missing:
            preview = missing[:12]
            message += (
                "\n\nUwagi:\n• "
                + "\n• ".join(preview)
            )

            if len(missing) > 12:
                message += (
                    f"\n… oraz {len(missing) - 12} kolejnych"
                )

        # Wynik pokazujemy bez dodatkowego okna modalnego.
        # Po resecie interfejsu szczegóły pozostają dostępne
        # w przewijanym polu pod paskiem postępu.
        details_lines = [
            f"Pobrano paczek powiatowych: {len(seen_urls)}",
            f"Zapisano warstw: {len(added)}",
            "",
            "Zapisano i dodano:",
        ]
        details_lines.extend(
            f"• {item}" for item in added
        )

        if missing:
            details_lines.extend([
                "",
                "Brakujące / pominięte elementy:",
            ])
            details_lines.extend(
                f"• {item}" for item in missing
            )

        details_text = "\n".join(details_lines)

        self._reset_after_success()

        self.result_details.setPlainText(details_text)
        self.result_details.setVisible(True)
        self.status.setText("")
        self.status.setVisible(False)

    def start_download(self):
        plan = self.selected_plan()

        if not plan:
            QMessageBox.warning(
                self,
                "QuickBDOT",
                "Zaznacz przynajmniej jedną klasę.",
            )
            return

        output = self._normalized_output_path()

        if not output:
            QMessageBox.warning(
                self,
                "QuickBDOT",
                "Najpierw wybierz miejsce zapisu.",
            )
            return

        self.download_btn.setEnabled(False)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.result_details.clear()
        self.result_details.setVisible(False)
        self.status.setVisible(True)
        self.status.setText("Rozpoczynam...")
        QApplication.processEvents()

        try:
            # -------------------------------------------------
            # TRYB: POWIATY WYBRANE RĘCZNIE
            # -------------------------------------------------
            if self.county_radio.isChecked():
                units = self.admin_selector.selected_units()

                if not units:
                    raise RuntimeError(
                        "Najpierw zaznacz przynajmniej jeden powiat."
                    )

                self._download_counties(
                    plan,
                    units,
                    mask_layer=None,
                )
                return

            # -------------------------------------------------
            # TRYB: AKTUALNY WIDOK / WARSTWA WEKTOROWA
            # -------------------------------------------------
            if self.vector_radio.isChecked():
                mask_layer = self.make_vector_mask_2180()
            else:
                mask_layer = self.make_extent_mask_2180()

            self.status.setText(
                "Sprawdzam, które powiaty przecinają obszar..."
            )
            QApplication.processEvents()

            mask_geometry = self._mask_geometry(
                mask_layer
            )

            units = self.admin_selector.intersecting_units(
                mask_geometry
            )

            if not units:
                raise RuntimeError(
                    "Obszar nie przecina żadnego powiatu PRG."
                )

            names = ", ".join(
                unit["name"]
                for unit in units[:5]
            )

            if len(units) > 5:
                names += f" i {len(units) - 5} kolejnych"

            self.status.setText(
                f"Obszar przecina {len(units)} powiatów: {names}"
            )
            QApplication.processEvents()

            self._download_counties(
                plan,
                units,
                mask_layer=mask_layer,
            )

        except Exception as error:
            self.status.setText(
                "Błąd: " + str(error)
            )

            QMessageBox.critical(
                self,
                "QuickBDOT – błąd",
                str(error),
            )

        finally:
            self.download_btn.setEnabled(True)

    def closeEvent(self, event):
        self.admin_selector.stop_selection(
            remove_layer=True
        )
        super().closeEvent(event)


class QuickBDOT:

    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.dialog = None

    def initGui(self):
        icon_path = Path(__file__).resolve().parent / "icons" / "quickbdot_logo.png"
        icon = QIcon(str(icon_path)) if icon_path.is_file() else QIcon()

        self.action = QAction(
            icon,
            "QuickBDOT",
            self.iface.mainWindow(),
        )

        self.action.setToolTip(
            "Pobierz wybrane klasy BDOT10k"
        )

        self.action.triggered.connect(
            self.run
        )

        self.iface.addPluginToMenu(
            "&QuickBDOT",
            self.action,
        )

        self.iface.addToolBarIcon(
            self.action
        )

    def unload(self):
        if self.dialog is not None:
            try:
                self.dialog.admin_selector.stop_selection(
                    remove_layer=True
                )
            except Exception:
                pass

        if self.action:
            self.iface.removePluginMenu(
                "&QuickBDOT",
                self.action,
            )
            self.iface.removeToolBarIcon(
                self.action
            )

    def run(self):
        if self.dialog is None:
            self.dialog = QuickBDOTDialog(
                self.iface,
                self.iface.mainWindow(),
            )

        self.dialog.refresh_vector_layers()
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()
