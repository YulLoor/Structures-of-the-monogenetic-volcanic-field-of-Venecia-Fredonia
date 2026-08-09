# Venecia–Fredonia structural GIS

ArcGIS Pro workspace for the structural map of the Venecia–Fredonia monogenetic volcanic field (Antioquia, Colombia). The cartography sits on a DEM/hillshade base and shows geological lineaments, named regional faults, the Sinclinal de Venecia, and volcanic bodies.

CRS: MAGNA-SIRGAS 2018 (Origen Nacional). Main map scale: **1:60,000**. Layout: **Diseño1** (letter landscape). The workspace is ~0.5 GB; GeoTIFFs are stored with Git LFS.

## Project layout

| Path | Contents |
|---|---|
| `01_Insumos/` | Source DEM tiles (Fredonia, Venecia) and merged DEM |
| `02_Rasters/` | Derived rasters: smoothed DEM, fill, flow dir/accum, drainage threshold, hillshade, profile curvature |
| `03_Vectores/` | Shapefiles (`Cuerpos_Volcanicos`, `Red_Hidrografica_V1000`) |
| `04_Scripts/` | Layout/symbology automation (`configurar_layout_carta_diseño1.py`) |
| `05_Salidas/` | Exported map PDF (`Diseño1.pdf`) |
| `Venecia_Fredonia_Analisis_Estructural.aprx` | **Canonical** ArcGIS Pro project — open this file |
| `Venecia_Fredonia_Analisis_Estructural/` | File geodatabase, toolbox, ImportLog, sandbox `MyProject1` |
| `MyProject2/` | Older scratch project (ignore for cartography) |

## Map layers (current)

**On by default (structural map):**

| Layer | Notes |
|---|---|
| `DEM_Venecia_Fredonia_Final.tif` / `DEM_Suave_Venecia_Fr_ProjectRaster.tif` | Elevation base |
| `Hillshade_DEM_V_Fr.tif` | Shaded relief (multiply / ~30% transparency) |
| `Lineamientos_VF` | Geological lineaments (GDB) |
| `Fallas Locales` | Local/regional faults (GDB, field `NombreFalla`) |
| `Pliegues Locales` | Folds — Sinclinal de Venecia (GDB) |
| `Volcanes` | Volcanic bodies |

**Off by default (support / analysis):** hydrology rasters (`Fill_Dem_VF`, `Flow_Dir`, `Flow_Accum`, `Red_Drenaje_P1000`), curvature surface, `Red_Hidrografica_V1000`, and the SGC 2015 Antioquia geology service.

### Legend groups (Diseño1)

- **Lineamientos geológicos** — verdadero (interpretado), inferido, literatura (López et al., 2006)
- **Fallas tectónicas** — Falla de Arma, Piedecuesta, San Jerónimo, La Cascajosa, Mistrató, San Juan
- **Pliegues** — Sinclinal de Venecia (light pink axis)
- **Cuerpos Volcánicos**

The map frame is centered on the Sinclinal de Venecia (~4698124, 2217500).

## Raster processing chain

1. Mosaic Fredonia + Venecia DEMs → `DEM_Venecia_Fredonia_Final.tif`
2. Project / smooth → `DEM_Suave_Venecia_Fr_ProjectRaster.tif`
3. Fill → Flow Direction → Flow Accumulation → `Red_Drenaje_P1000` (threshold 1000)
4. Hillshade + profile-curvature surface for lineament interpretation
5. Digitize / style structural layers in the GDB
6. Layout **Diseño1** → `05_Salidas/Diseño1.pdf`

## Opening the project

Open only:

`C:\PROYECTO_GIS_VF_Antigraviti\Venecia_Fredonia_Analisis_Estructural.aprx`

Do not open the nested `.aprx` inside the project folder (older map-only copy). Needs ArcGIS Pro with Spatial Analyst for the hydrology/DEM tools.

If you relocate the folder, update `ROOT` in `04_Scripts/configurar_layout_carta_diseño1.py`.

## Layout script

`04_Scripts/configurar_layout_carta_diseño1.py` applies the fault/lineament/fold/volcano symbology, recenters the map on the Sinclinal, updates layout **Diseño1**, and exports:

`05_Salidas/Diseño1.pdf` (300 DPI)

Run from the Python window in Pro (or any `arcpy` session pointed at this project).

## License

MIT — see `LICENSE`.
