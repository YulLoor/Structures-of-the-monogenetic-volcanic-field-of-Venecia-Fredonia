# Venecia–Fredonia structural GIS

ArcGIS Pro workspace for structural mapping of the Venecia–Fredonia volcanic field (Antioquia, Colombia). DEM-based terrain and hydrology products sit alongside lineaments, faults, folds, and volcanic bodies; the main cartographic product is a structural map at 1:60,000.

Working CRS in the datasets is MAGNA-SIRGAS 2018 (Origen Nacional). The folder is about half a gigabyte — several GeoTIFFs are large.

## Layout

| Folder / file | Role |
|---|---|
| `01_Insumos/` | Source DEMs (Fredonia / Venecia tiles and the merged DEM) |
| `02_Rasters/` | Derived surfaces: smoothed DEM, fill, flow dir/accum, drainage threshold, hillshade, profile curvature |
| `03_Vectores/` | Shapefiles (volcanic bodies, hydro network) |
| `04_Scripts/` | `arcpy` layout / symbology automation |
| `05_Salidas/` | Exported structural map PDF |
| `Venecia_Fredonia_Analisis_Estructural.aprx` | Main ArcGIS Pro project |
| `Venecia_Fredonia_Analisis_Estructural/` | Project GDB, toolbox, and Pro side folders |

There are also sandbox projects (`MyProject2`, nested `MyProject1`) left over from earlier Pro sessions; the canonical map is the root `.aprx`.

## Processing chain (roughly)

1. Mosaic Fredonia + Venecia DEMs → `DEM_Venecia_Fredonia_Final.tif`
2. Project / smooth → `DEM_Suave_Venecia_Fr_ProjectRaster.tif`
3. Hydrology: Fill → Flow Direction → Flow Accumulation → drainage network (`Red_Drenaje_P1000`, accumulation threshold 1000)
4. Hillshade and profile-curvature surface for lineament work
5. Structural layers in the GDB / map (lineaments, local faults & folds, volcanoes)
6. Layout “Diseño1” → PDF under `05_Salidas/`

## Opening the project

Open `Venecia_Fredonia_Analisis_Estructural.aprx` in ArcGIS Pro (Spatial Analyst for the raster tools used in the chain). Paths in the layout script assume this directory lives at:

`C:\PROYECTO_GIS_VF_Antigraviti`

If you move the folder, update `ROOT` in `04_Scripts/configurar_layout_carta_diseño1.py` before running it.

## Layout script

`04_Scripts/configurar_layout_carta_diseño1.py` styles the structural layers, sets up the letter-landscape layout (main map ~1:60,000, regional inset), and exports:

`05_Salidas/Mapa_Estructural_VF_Carta.pdf`

Run it from the Python window in Pro, or any environment that has `arcpy` pointed at this project.

Lineament citation used on the map: López et al. (2006).

## License

MIT — see `LICENSE`.
