# QuickBDOT 0.0.38

**BDOT10k selection, download, export and styling directly in QGIS.**

QuickBDOT is a QGIS plugin for working with Polish **BDOT10k** topographic data. It automates data download, class/type selection, export and cartographic presentation directly in a QGIS project.

## Features

- download BDOT10k data for the current map extent,
- download data using the geometry of a polygon layer,
- select one or more Polish counties directly on the map,
- three-level selection of BDOT10k categories, classes and object types,
- export to **GeoPackage (.gpkg)** or **ESRI Shapefile (.shp)**,
- automatic layer ordering,
- optional BDOT10k symbology and labels,
- automatic output CRS normalization to **PL-1992 / EPSG:2180** where required,
- progress reporting and processing messages.

## Compatibility

- **QGIS 3.36 or newer**
- **QGIS 4.x**

QuickBDOT uses the `qgis.PyQt` compatibility layer and is intended to work with both Qt5-based QGIS 3 and Qt6-based QGIS 4.

## Area selection modes

QuickBDOT provides three ways to define the working area:

1. **Current map extent** — downloads BDOT10k data for the area currently visible in QGIS.
2. **Polygon layer** — downloads and clips data to the geometry of a selected polygon layer.
3. **County selection** — allows one or more counties to be selected interactively on the map.

## BDOT10k layer selection

The layer tree has three levels:

- category,
- class,
- object type.

You can select an entire category/class or only individual object types.

## Output formats

### GeoPackage

All selected layers are stored in one `.gpkg` file.

### Shapefile

Each selected BDOT10k class is stored as a separate Shapefile. QuickBDOT converts unsupported curved geometries to Shapefile-compatible geometry types before export. If an output Shapefile already exists and is locked by QGIS/OGR, a new free filename is used instead of forcing an unsafe overwrite.

## Cartographic presentation

When **Apply labels and symbology** is enabled, QuickBDOT applies prepared BDOT10k styling and labeling where available. When disabled, layers are added in their raw form.

Selected QML and SVG cartographic resources originate from **BDOT10k_GML_SHP_Loader 2.0.1**. See `NOTICE.txt` for attribution and licensing details.

## Installation from a ZIP file

1. Open QGIS.
2. Go to **Plugins → Manage and Install Plugins…**.
3. Open **Install from ZIP**.
4. Select the QuickBDOT ZIP package.
5. Click **Install Plugin**.

After publication in the official QGIS Plugin Repository, QuickBDOT can be installed directly from the **All** tab in the QGIS plugin manager.

## Repository and issue tracker

Source code: https://github.com/maciejgalant/QuickBDOT  
Issues: https://github.com/maciejgalant/QuickBDOT/issues

## Author

**Maciej Galant**  
Email: **magal.pl@wp.pl**

## License

QuickBDOT is distributed under the **GNU General Public License v3.0 (GPL-3.0)**. See `LICENSE` for the complete license text.

Third-party resources included with the plugin retain their respective copyright notices and license terms. See `NOTICE.txt`.
