# -*- coding: utf-8 -*-
"""
Diseño2 — Mapa litológico/cronoestratigráfico (independiente del estructural).

- No modifica Map_Estructural ni Diseño1.
- Opera solo sobre Mapa_Litologico + Diseño2.
- Elimina Mapa_Crono si existe.
- Recorta 'Unidad Cronoestratigráfica' (SGC Atlas) a la extensión
  (envelope) de Fallas_Locales.

Ejecutar con el Python de ArcGIS Pro:
  \"C:\\Program Files\\ArcGIS\\Pro\\bin\\Python\\envs\\arcgispro-py3\\python.exe\" ^
    04_Scripts\\configurar_layout_diseño2.py
"""

from __future__ import annotations

import datetime as _dt
import os
import sys
import traceback

import arcpy

# ---------------------------------------------------------------------------
# Rutas y constantes
# ---------------------------------------------------------------------------
ROOT = r"C:\PROYECTO_GIS_VF_Antigraviti"
APRX_PATH = os.path.join(ROOT, "Venecia_Fredonia_Analisis_Estructural.aprx")
GDB = os.path.join(
    ROOT,
    "Venecia_Fredonia_Analisis_Estructural",
    "Venecia_Fredonia_Analisis_Estructural.gdb",
)
HILLSHADE = os.path.join(ROOT, "02_Rasters", "Hillshade_DEM_V_Fr.tif")
DEM = os.path.join(ROOT, "02_Rasters", "DEM_Suave_Venecia_Fr_ProjectRaster.tif")
if not os.path.exists(DEM):
    DEM = os.path.join(ROOT, "01_Insumos", "DEM_Venecia_Fredonia_Final.tif")

FALLAS_FC = os.path.join(GDB, "Fallas_Locales")

PDF_PATH = os.path.join(ROOT, "05_Salidas", "Mapa_Cronoestratigrafico_VF_Carta.pdf")
PDF_FALLBACK = os.path.join(ROOT, "Mapa_Cronoestratigrafico_VF_Carta.pdf")
BACKUP_DIR = os.path.join(ROOT, ".backups")

MAP_ESTRUCTURAL = "Map_Estructural"
MAP_LITO = "Mapa_Litologico"
MAP_CRONO_OLD = "Mapa_Crono"
LAYOUT1 = "Diseño1"
LAYOUT2 = "Diseño2"

CRONO_LAYER_NAME = "Unidad Cronoestratigráfica"
CRONO_SERVICE_URL = (
    "https://srvags.sgc.gov.co/arcgis/rest/services/"
    "Atlas_Geologico_Colombiano/Atlas_Geologico_Colombia/MapServer/13"
)
CRONO_CLIP_FC = "Unidades_Cronoestratigraficas_clip"
CLIP_POLY_FC = "Fallas_Locales_envelope"

SCALE = 60000.0
INSET_SCALE = 400000.0
MAP_CENTER_X = 4698124.0
MAP_CENTER_Y = 2217500.0

PAGE_W = 11.0
PAGE_H = 8.5
MARGIN = 0.30
RIGHT_COL_W = 2.70
SCALE_TEXT = "Escala 1:60000"
TITLE_TEXT = (
    "Mapa cronoestratigráfico del campo volcánico Venecia-Fredonia\r\n"
    + SCALE_TEXT
)


def find_layout_by_name(aprx, name):
    for lyt in aprx.listLayouts():
        if lyt.name == name or lyt.name.replace(" ", "") == name.replace(" ", ""):
            return lyt
    for lyt in aprx.listLayouts():
        if name.endswith("2") and lyt.name.endswith("2") and "Dise" in lyt.name:
            return lyt
        if (
            name.endswith("1")
            and lyt.name.endswith("1")
            and not lyt.name.endswith("2")
            and "Dise" in lyt.name
        ):
            return lyt
    return None


def ensure_backup():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = os.path.join(
        BACKUP_DIR, f"Venecia_Fredonia_Analisis_Estructural_{stamp}.aprx"
    )
    aprx = arcpy.mp.ArcGISProject(APRX_PATH)
    aprx.saveACopy(dest)
    print(f"  OK Backup: {dest}")
    return dest


def get_or_rename_structural_map(aprx):
    """Asegura Map_Estructural y que Diseño1 apunte a él."""
    maps_est = aprx.listMaps(MAP_ESTRUCTURAL)
    if maps_est:
        amap = maps_est[0]
    else:
        maps = aprx.listMaps("Map")
        if not maps:
            raise RuntimeError("No existe mapa 'Map' ni 'Map_Estructural'")
        amap = maps[0]
        amap.name = MAP_ESTRUCTURAL
        print(f"  OK Renombrado Map -> {MAP_ESTRUCTURAL}")

    lyt1 = find_layout_by_name(aprx, LAYOUT1)
    if lyt1 is None:
        for lyt in aprx.listLayouts():
            if abs(lyt.pageWidth - 11.0) < 0.1 and abs(lyt.pageHeight - 8.5) < 0.1:
                if not lyt.name.endswith("2"):
                    lyt1 = lyt
                    break
    if lyt1 is None:
        raise RuntimeError("No se encontró Diseño1")

    for mf in lyt1.listElements("MAPFRAME_ELEMENT"):
        try:
            mf.map = amap
        except Exception as ex:
            print(f"  Aviso asignar {mf.name} -> {MAP_ESTRUCTURAL}: {ex}")

    for lyr in amap.listLayers():
        n = lyr.name.lower()
        if CRONO_LAYER_NAME.lower() in n or "crono" in n:
            lyr.visible = False
            print(f"  OK Oculta en estructural: {lyr.name}")

    print(f"  OK Diseño1 enlazado a {amap.name}")
    return amap, lyt1


def delete_mapa_crono(aprx, fallback_map):
    """Reasigna marcos que usen Mapa_Crono y elimina ese mapa."""
    for lyt in aprx.listLayouts():
        for mf in lyt.listElements("MAPFRAME_ELEMENT"):
            if mf.map and mf.map.name == MAP_CRONO_OLD:
                try:
                    mf.map = fallback_map
                    print(f"  OK Reasignado {lyt.name}/{mf.name} -> {fallback_map.name}")
                except Exception as ex:
                    print(f"  Aviso reasignar marco: {ex}")

    for amap in list(aprx.listMaps()):
        if amap.name == MAP_CRONO_OLD:
            try:
                aprx.deleteItem(amap)
                print(f"  OK Eliminado mapa {MAP_CRONO_OLD}")
            except Exception as ex:
                # Si Pro tiene el mapa abierto, intentar renombrar/vaciar
                print(f"  Aviso deleteItem {MAP_CRONO_OLD}: {ex}")
                try:
                    amap.name = "_DELETE_Mapa_Crono"
                    print("  OK Renombrado a _DELETE_Mapa_Crono (eliminar manualmente en Pro si queda)")
                except Exception as ex2:
                    print(f"  ERROR no se pudo eliminar/renombrar Mapa_Crono: {ex2}")


def get_or_create_lito_map(aprx):
    existing = aprx.listMaps(MAP_LITO)
    if existing:
        print(f"  OK Mapa existente: {MAP_LITO}")
        return existing[0]
    amap = aprx.createMap(MAP_LITO, "Map")
    try:
        amap.spatialReference = arcpy.SpatialReference(9377)
    except Exception:
        pass
    print(f"  OK Creado mapa {MAP_LITO}")
    return amap


def get_or_create_layout2(aprx, lyt1, lito_map):
    """Recrea Diseño2 limpio (Carta) apuntando a Mapa_Litologico."""
    for lyt in list(aprx.listLayouts()):
        if lyt.name == LAYOUT2 or (
            lyt.name.endswith("2") and "Dise" in lyt.name and lyt is not lyt1
        ):
            try:
                aprx.deleteItem(lyt)
                print(f"  OK Eliminado layout previo: {lyt.name}")
            except Exception as ex:
                print(f"  Aviso deleteItem layout: {ex}")

    lyt2 = aprx.createLayout(PAGE_W, PAGE_H, "INCH", LAYOUT2)
    print(f"  OK Creado layout limpio: {lyt2.name}")

    map_w = PAGE_W - 2 * MARGIN - RIGHT_COL_W - 0.15
    map_h = PAGE_H - MARGIN - 0.80
    corners = [
        arcpy.Point(MARGIN, 0.80),
        arcpy.Point(MARGIN + map_w, 0.80),
        arcpy.Point(MARGIN + map_w, 0.80 + map_h),
        arcpy.Point(MARGIN, 0.80 + map_h),
        arcpy.Point(MARGIN, 0.80),
    ]
    mf = lyt2.createMapFrame(
        arcpy.Polygon(arcpy.Array(corners)), lito_map, "Marco de mapa"
    )
    mf.camera.scale = SCALE
    mf.camera.X = MAP_CENTER_X
    mf.camera.Y = MAP_CENTER_Y

    inset_h = 3.10
    ix0 = PAGE_W - MARGIN - RIGHT_COL_W
    iy0 = PAGE_H - MARGIN - inset_h
    icorners = [
        arcpy.Point(ix0, iy0),
        arcpy.Point(ix0 + RIGHT_COL_W, iy0),
        arcpy.Point(ix0 + RIGHT_COL_W, iy0 + inset_h),
        arcpy.Point(ix0, iy0 + inset_h),
        arcpy.Point(ix0, iy0),
    ]
    inset = lyt2.createMapFrame(
        arcpy.Polygon(arcpy.Array(icorners)), lito_map, "Marco de mapa 1"
    )
    inset.camera.scale = INSET_SCALE
    inset.camera.X = MAP_CENTER_X
    inset.camera.Y = MAP_CENTER_Y

    try:
        na = lyt2.createMapSurroundElement(
            arcpy.Point(MARGIN + 0.12, PAGE_H - MARGIN - 0.85),
            "North_Arrow",
            mf,
            name="Flecha de norte",
        )
        na.elementWidth = 0.40
        na.elementHeight = 0.60
    except Exception as ex:
        print(f"  Aviso norte: {ex}")

    try:
        sb = lyt2.createMapSurroundElement(
            arcpy.Point(MARGIN + 0.08, 0.28),
            "Scale_Bar",
            mf,
            name="Barra de escala",
        )
        sb.elementWidth = 2.6
        sb.elementHeight = 0.32
    except Exception as ex:
        print(f"  Aviso escala: {ex}")

    try:
        aprx.createTextElement(
            lyt2,
            arcpy.Point(MARGIN + 2.85, 0.32),
            "POINT",
            SCALE_TEXT,
            text_size=11,
            font_family_name="Arial",
            font_style_name="Bold",
            name="Texto",
        )
    except Exception as ex:
        print(f"  Aviso texto escala: {ex}")

    return lyt2


def envelope_polygon_from_fc(in_fc, out_fc):
    """Polígono = envelope (tamaño/extensión) de Fallas_Locales."""
    if arcpy.Exists(out_fc):
        arcpy.management.Delete(out_fc)
    desc = arcpy.Describe(in_fc)
    ext = desc.extent
    sr = desc.spatialReference
    arcpy.management.CreateFeatureclass(
        os.path.dirname(out_fc),
        os.path.basename(out_fc),
        "POLYGON",
        spatial_reference=sr,
    )
    array = arcpy.Array(
        [
            arcpy.Point(ext.XMin, ext.YMin),
            arcpy.Point(ext.XMin, ext.YMax),
            arcpy.Point(ext.XMax, ext.YMax),
            arcpy.Point(ext.XMax, ext.YMin),
            arcpy.Point(ext.XMin, ext.YMin),
        ]
    )
    poly = arcpy.Polygon(array, sr)
    with arcpy.da.InsertCursor(out_fc, ["SHAPE@"]) as cur:
        cur.insertRow([poly])
    print(f"  OK Envelope Fallas_Locales -> {out_fc}")
    print(
        f"    extent [{ext.XMin:.1f}, {ext.YMin:.1f}] - [{ext.XMax:.1f}, {ext.YMax:.1f}]"
    )
    return out_fc


def find_crono_source(aprx):
    for amap in aprx.listMaps():
        for lyr in amap.listLayers():
            n = lyr.name.lower()
            if "crono" in n or lyr.name == CRONO_LAYER_NAME:
                try:
                    ds = lyr.dataSource
                except Exception:
                    ds = ""
                # Preferir servicio/capa original, no el clip previo
                if CRONO_CLIP_FC in str(ds):
                    continue
                print(f"  Fuente encontrada en {amap.name}: {lyr.name}")
                print(f"    {ds}")
                return ds or CRONO_SERVICE_URL
    print("  Usando URL Atlas SGC")
    return CRONO_SERVICE_URL


def clip_crono_to_fallas(aprx):
    """Recorta unidades cronoestratigráficas al envelope de Fallas_Locales."""
    if not arcpy.Exists(FALLAS_FC):
        raise FileNotFoundError(FALLAS_FC)

    arcpy.env.overwriteOutput = True
    arcpy.env.outputCoordinateSystem = arcpy.SpatialReference(9377)

    clip_poly = os.path.join(GDB, CLIP_POLY_FC)
    out_fc = os.path.join(GDB, CRONO_CLIP_FC)
    envelope_polygon_from_fc(FALLAS_FC, clip_poly)

    source = find_crono_source(aprx)
    tmp_fc = os.path.join(GDB, "Unidades_Crono_tmp_extent")

    # Extensión de export = envelope de fallas
    arcpy.env.extent = arcpy.Describe(FALLAS_FC).extent
    if arcpy.Exists(tmp_fc):
        arcpy.management.Delete(tmp_fc)

    try:
        arcpy.conversion.ExportFeatures(source, tmp_fc)
        print(f"  OK ExportFeatures -> {tmp_fc}")
    except Exception as ex1:
        print(f"  Aviso ExportFeatures: {ex1}")
        try:
            arcpy.management.CopyFeatures(source, tmp_fc)
            print(f"  OK CopyFeatures -> {tmp_fc}")
        except Exception as ex2:
            raise RuntimeError(
                "No se pudo descargar/copiar Unidades Cronoestratigráficas. "
                f"Fuente={source}. Errores: {ex1} | {ex2}"
            )

    if arcpy.Exists(out_fc):
        arcpy.management.Delete(out_fc)
    arcpy.analysis.Clip(tmp_fc, clip_poly, out_fc)
    count = int(arcpy.management.GetCount(out_fc)[0])
    print(f"  OK Clip (tamaño Fallas_Locales) -> {out_fc} ({count} features)")

    try:
        arcpy.management.Delete(tmp_fc)
    except Exception:
        pass

    arcpy.env.extent = None
    return out_fc


def add_layer_if_missing(amap, path_or_layer, name=None):
    target_name = name or os.path.splitext(os.path.basename(str(path_or_layer)))[0]
    for lyr in amap.listLayers():
        if lyr.name == target_name:
            return lyr
    try:
        lyr = amap.addDataFromPath(path_or_layer)
        if name:
            try:
                lyr.name = name
            except Exception:
                pass
        print(f"  OK Añadida: {lyr.name}")
        return lyr
    except Exception as ex:
        print(f"  ERROR addDataFromPath {path_or_layer}: {ex}")
        return None


def apply_crono_atlas_symbology(aprx, clip_lyr):
    """Copia simbología UniqueValue del Atlas (AUCR_CODG) al clip; fallback RGB."""
    src = None
    for amap in aprx.listMaps():
        for lyr in amap.listLayers():
            n = lyr.name
            if n == CRONO_LAYER_NAME or (
                "crono" in n.lower()
                and CRONO_CLIP_FC not in n
                and "Unidades_Crono" not in n
            ):
                src = lyr
                break
        if src:
            break

    if src is not None:
        try:
            arcpy.management.ApplySymbologyFromLayer(clip_lyr, src)
            rtype = type(clip_lyr.getDefinition("V3").renderer).__name__
            if rtype == "CIMUniqueValueRenderer":
                ncls = len(clip_lyr.getDefinition("V3").renderer.groups[0].classes or [])
                print(f"  OK Simbología Atlas aplicada ({ncls} clases)")
                try:
                    clip_lyr.transparency = 0
                except Exception:
                    pass
                return True
        except Exception as ex:
            print(f"  Aviso ApplySymbologyFromLayer: {ex}")
        try:
            src_cim = src.getDefinition("V3")
            dst_cim = clip_lyr.getDefinition("V3")
            dst_cim.renderer = src_cim.renderer
            clip_lyr.setDefinition(dst_cim)
            print("  OK Renderer CIM Atlas copiado")
            try:
                clip_lyr.transparency = 0
            except Exception:
                pass
            return True
        except Exception as ex:
            print(f"  Aviso copia CIM: {ex}")

    # Fallback: R,G,B del feature class
    try:
        fc = clip_lyr.dataSource
        lookup = {}
        with arcpy.da.SearchCursor(
            fc, ["AUCR_CODG", "AUCR_SIMBL", "ACUC_DESC", "R", "G", "B"]
        ) as cur:
            for codg, simbl, desc, r, g, b in cur:
                if codg is None or codg in lookup:
                    continue
                label = (simbl or desc or str(codg)).strip()
                lookup[codg] = (
                    label,
                    int(r) if r is not None else 220,
                    int(g) if g is not None else 220,
                    int(b) if b is not None else 180,
                )

        def _rgb(rr, gg, bb, a=100):
            c = arcpy.cim.CreateCIMObjectFromClassName("CIMRGBColor", "V3")
            c.values = [float(rr), float(gg), float(bb), float(a)]
            return c

        def _sym(rr, gg, bb):
            fill = arcpy.cim.CreateCIMObjectFromClassName("CIMSolidFill", "V3")
            fill.color = _rgb(rr, gg, bb)
            stroke = arcpy.cim.CreateCIMObjectFromClassName("CIMSolidStroke", "V3")
            stroke.color = _rgb(80, 80, 80)
            stroke.width = 0.4
            stroke.enable = True
            poly = arcpy.cim.CreateCIMObjectFromClassName("CIMPolygonSymbol", "V3")
            poly.symbolLayers = [stroke, fill]
            ref = arcpy.cim.CreateCIMObjectFromClassName("CIMSymbolReference", "V3")
            ref.symbol = poly
            return ref

        renderer = arcpy.cim.CreateCIMObjectFromClassName(
            "CIMUniqueValueRenderer", "V3"
        )
        renderer.fields = ["AUCR_CODG"]
        renderer.useDefaultSymbol = False
        group = arcpy.cim.CreateCIMObjectFromClassName("CIMUniqueValueGroup", "V3")
        group.heading = "Unidades cronoestratigráficas"
        classes = []
        for codg, (label, rr, gg, bb) in sorted(
            lookup.items(), key=lambda x: str(x[1][0])
        ):
            uv = arcpy.cim.CreateCIMObjectFromClassName("CIMUniqueValue", "V3")
            uv.fieldValues = [str(codg)]
            cls = arcpy.cim.CreateCIMObjectFromClassName("CIMUniqueValueClass", "V3")
            cls.label = label
            cls.visible = True
            cls.values = [uv]
            cls.symbol = _sym(rr, gg, bb)
            classes.append(cls)
        group.classes = classes
        renderer.groups = [group]
        cim = clip_lyr.getDefinition("V3")
        cim.renderer = renderer
        clip_lyr.setDefinition(cim)
        try:
            clip_lyr.transparency = 0
        except Exception:
            pass
        print(f"  OK Simbología RGB Atlas ({len(classes)} clases)")
        return True
    except Exception as ex:
        print(f"  ERROR simbología crono: {ex}")
        return False


def configure_lito_map_layers(amap, crono_fc, aprx=None):
    """Hillshade + DEM + unidades (clip Fallas) + Fallas Locales."""
    add_layer_if_missing(amap, DEM, os.path.basename(DEM))
    add_layer_if_missing(amap, HILLSHADE, os.path.basename(HILLSHADE))
    crono_lyr = add_layer_if_missing(amap, crono_fc, CRONO_CLIP_FC)

    if arcpy.Exists(FALLAS_FC):
        fl = add_layer_if_missing(amap, FALLAS_FC, "Fallas Locales")
        if fl:
            fl.visible = True

    for lyr in amap.listLayers():
        if lyr.name == "Topographic":
            lyr.visible = False
        if "Hillshade" in lyr.name:
            try:
                lyr.transparency = 40
            except Exception:
                pass
            lyr.visible = True
        if lyr.name == CRONO_CLIP_FC or (crono_lyr and lyr.name == crono_lyr.name):
            lyr.visible = True

    if crono_lyr is not None and aprx is not None:
        apply_crono_atlas_symbology(aprx, crono_lyr)
    elif crono_lyr is not None:
        # Intentar con mapas del proyecto abierto vía layer parent no disponible;
        # al menos quitar transparencia que lava colores
        try:
            crono_lyr.transparency = 0
        except Exception:
            pass

    names = [
        "Fallas Locales",
        CRONO_CLIP_FC,
        os.path.basename(HILLSHADE),
        os.path.basename(DEM),
    ]
    layers = {lyr.name: lyr for lyr in amap.listLayers()}
    for i, name in enumerate(names):
        if name not in layers:
            continue
        lyr = layers[name]
        if i == 0:
            ref = amap.listLayers()[0]
            if lyr != ref:
                try:
                    amap.moveLayer(ref, lyr, "BEFORE")
                except Exception:
                    pass
            continue
        prev = names[i - 1]
        if prev in layers:
            try:
                amap.moveLayer(layers[prev], lyr, "AFTER")
            except Exception:
                pass

    print(f"  OK Capas {MAP_LITO} configuradas")
    return crono_lyr


def configure_page_and_frames(lyt, amap):
    lyt.pageUnits = "INCH"
    try:
        lyt.changePageSize(PAGE_W, PAGE_H, resize_elements=False)
    except TypeError:
        lyt.pageWidth = PAGE_W
        lyt.pageHeight = PAGE_H

    map_w = PAGE_W - 2 * MARGIN - RIGHT_COL_W - 0.15
    map_h = PAGE_H - MARGIN - 0.80

    mfs = lyt.listElements("MAPFRAME_ELEMENT", "Marco de mapa")
    if not mfs:
        mfs = [e for e in lyt.listElements("MAPFRAME_ELEMENT") if e.name == "Marco de mapa"]
    if not mfs:
        mfs = lyt.listElements("MAPFRAME_ELEMENT")
    mf = mfs[0]
    mf.map = amap
    mf.elementPositionX = MARGIN
    mf.elementPositionY = 0.80
    mf.elementWidth = map_w
    mf.elementHeight = map_h
    mf.camera.scale = SCALE
    mf.camera.X = MAP_CENTER_X
    mf.camera.Y = MAP_CENTER_Y

    insets = lyt.listElements("MAPFRAME_ELEMENT", "Marco de mapa 1")
    if insets:
        inset = insets[0]
        inset.map = amap
        inset.elementWidth = RIGHT_COL_W
        inset.elementHeight = 3.10
        inset.elementPositionX = PAGE_W - MARGIN - RIGHT_COL_W
        inset.elementPositionY = PAGE_H - MARGIN - inset.elementHeight
        inset.camera.X = MAP_CENTER_X
        inset.camera.Y = MAP_CENTER_Y
        inset.camera.scale = INSET_SCALE

    for na in lyt.listElements("MAPSURROUND_ELEMENT", "Flecha de norte"):
        na.elementWidth = 0.40
        na.elementHeight = 0.60
        na.elementPositionX = MARGIN + 0.12
        na.elementPositionY = PAGE_H - MARGIN - 0.85

    for sb in lyt.listElements("MAPSURROUND_ELEMENT", "Barra de escala"):
        sb.elementWidth = 2.6
        sb.elementHeight = 0.32
        sb.elementPositionX = MARGIN + 0.08
        sb.elementPositionY = 0.28

    for te in lyt.listElements("TEXT_ELEMENT", "Texto"):
        te.text = SCALE_TEXT

    print("  OK Página/marcos Diseño2 1:60.000")
    return mf


def configure_title(aprx, lyt):
    title_name = "Titulo_mapa"
    bg_name = "Titulo_fondo"
    map_w = PAGE_W - 2 * MARGIN - RIGHT_COL_W - 0.15
    x0, y0 = MARGIN, PAGE_H - 0.55
    x1, y1 = MARGIN + map_w, PAGE_H - 0.08
    corners = [
        arcpy.Point(x0, y0),
        arcpy.Point(x1, y0),
        arcpy.Point(x1, y1),
        arcpy.Point(x0, y1),
        arcpy.Point(x0, y0),
    ]
    poly = arcpy.Polygon(arcpy.Array(corners))

    bg = None
    for ge in lyt.listElements("GRAPHIC_ELEMENT"):
        if ge.name == bg_name:
            bg = ge
            break
    if bg is None:
        try:
            bg = aprx.createPredefinedGraphicElement(
                lyt, poly, "RECTANGLE", name=bg_name
            )
        except Exception:
            bg = aprx.createGraphicElement(lyt, poly, name=bg_name)
    bg.elementPositionX = x0
    bg.elementPositionY = y0
    bg.elementWidth = x1 - x0
    bg.elementHeight = y1 - y0
    bg.visible = True

    existing = None
    for te in lyt.listElements("TEXT_ELEMENT"):
        if te.name == title_name:
            existing = te
            break
    if existing is None:
        existing = aprx.createTextElement(
            lyt,
            poly,
            "POLYGON",
            TITLE_TEXT,
            text_size=13,
            font_family_name="Arial",
            font_style_name="Bold",
            name=title_name,
        )
    else:
        existing.text = TITLE_TEXT
    existing.elementPositionX = x0
    existing.elementPositionY = y0
    existing.elementWidth = x1 - x0
    existing.elementHeight = y1 - y0
    existing.visible = True
    print("  OK Título Diseño2")
    return existing


def configure_legend(lyt, mf, amap):
    legend = None
    for leg in lyt.listElements("LEGEND_ELEMENT"):
        if leg.name == "Leyenda" or legend is None:
            legend = leg
            legend.visible = True
    if legend is None:
        x0 = PAGE_W - MARGIN - RIGHT_COL_W
        y0 = MARGIN + 0.55
        y1 = PAGE_H - MARGIN - 3.25
        corners = [
            arcpy.Point(x0, y0),
            arcpy.Point(x0 + RIGHT_COL_W, y0),
            arcpy.Point(x0 + RIGHT_COL_W, y1),
            arcpy.Point(x0, y1),
            arcpy.Point(x0, y0),
        ]
        legend = lyt.createMapSurroundElement(
            arcpy.Polygon(arcpy.Array(corners)), "LEGEND", mf, name="Leyenda"
        )

    legend.elementPositionX = PAGE_W - MARGIN - RIGHT_COL_W
    legend.elementPositionY = MARGIN + 0.55
    legend.elementWidth = RIGHT_COL_W
    legend.elementHeight = max(2.5, PAGE_H - MARGIN - 3.25 - (MARGIN + 0.55))
    legend.showTitle = True
    legend.title = "Leyenda"
    try:
        legend.fittingStrategy = "AdjustColumnsAndSize"
        legend.columnCount = 1
    except Exception:
        pass

    keep = {"Litología", "Muestras CVMVF"}
    existing = {it.name for it in legend.items}
    for name in keep:
        if name not in existing:
            try:
                lyrs = amap.listLayers(name)
                if lyrs:
                    legend.addItem(lyrs[0])
            except Exception as ex:
                print(f"  Aviso addItem {name}: {ex}")
    for item in list(legend.items):
        if item.name not in keep:
            try:
                legend.removeItem(item)
            except Exception:
                pass

    print(f"  OK Leyenda Diseño2: {[i.name for i in legend.items]}")
    return legend


def export_pdf(lyt):
    os.makedirs(os.path.dirname(PDF_PATH), exist_ok=True)
    candidates = [PDF_PATH, PDF_FALLBACK]
    stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    candidates.append(
        os.path.join(ROOT, f"Mapa_Cronoestratigrafico_VF_Carta_{stamp}.pdf")
    )
    last_err = None
    for out in candidates:
        try:
            if os.path.exists(out):
                try:
                    os.remove(out)
                except OSError:
                    continue
            lyt.exportToPDF(out, resolution=300)
            print(f"  OK PDF: {out}")
            return out
        except Exception as ex:
            last_err = ex
            print(f"  Aviso PDF {out}: {ex}")

    png = os.path.join(ROOT, "05_Salidas", "Mapa_Cronoestratigrafico_VF_Carta.png")
    lyt.exportToPNG(png, resolution=300)
    print(f"  OK PNG (PDF no disponible desde ArcPy): {png}")
    print(f"    Detalle PDF: {last_err}")
    print("    En Pro: Diseño2 → Share → Export → PDF")
    return png


def verify_isolation(aprx):
    m_est = aprx.listMaps(MAP_ESTRUCTURAL)[0]
    m_lito = aprx.listMaps(MAP_LITO)[0]
    lyt1 = find_layout_by_name(aprx, LAYOUT1)
    lyt2 = find_layout_by_name(aprx, LAYOUT2)
    map_names = [m.name for m in aprx.listMaps()]
    print("\n=== Verificación ===")
    print(f"  Maps: {map_names}")
    assert MAP_CRONO_OLD not in map_names, "Mapa_Crono aún existe"
    residuals = [n for n in map_names if n.startswith("_DELETE")]
    if residuals:
        print(f"  AVISO mapas residuales: {residuals}")
    for mf in lyt1.listElements("MAPFRAME_ELEMENT"):
        print(f"  Diseño1 / {mf.name} -> {mf.map.name if mf.map else None}")
        assert mf.map and mf.map.name == MAP_ESTRUCTURAL
    for mf in lyt2.listElements("MAPFRAME_ELEMENT"):
        print(f"  Diseño2 / {mf.name} -> {mf.map.name if mf.map else None}")
        assert mf.map and mf.map.name == MAP_LITO
    est_names = {lyr.name for lyr in m_est.listLayers()}
    lito_names = {lyr.name for lyr in m_lito.listLayers()}
    print(f"  Estructural tiene clip crono? {CRONO_CLIP_FC in est_names}")
    print(f"  Mapa_Litologico tiene clip crono? {CRONO_CLIP_FC in lito_names}")
    if MAP_CRONO_OLD in map_names or any(n.startswith("_DELETE") for n in map_names):
        print("  AVISO: queda un mapa residual a borrar en Pro")
    print("  OK Aislamiento verificado")


def main():
    print("=" * 60)
    print("Diseño2 — Mapa_Litologico (sin Mapa_Crono)")
    print("=" * 60)

    if not os.path.exists(APRX_PATH):
        raise FileNotFoundError(APRX_PATH)
    if not arcpy.Exists(FALLAS_FC):
        raise FileNotFoundError(FALLAS_FC)

    need_backup = True
    if os.path.isdir(BACKUP_DIR):
        today = _dt.datetime.now().strftime("%Y%m%d")
        for fn in os.listdir(BACKUP_DIR):
            if today in fn and fn.endswith(".aprx"):
                need_backup = False
                break
    if need_backup:
        print("\n[0] Backup APRX")
        ensure_backup()
    else:
        print("\n[0] Backup reciente encontrado — se omite")

    aprx = arcpy.mp.ArcGISProject(APRX_PATH)

    print("\n[1] Fijar Diseño1 -> Map_Estructural")
    structural_map, lyt1 = get_or_rename_structural_map(aprx)

    print("\n[2] Crear Mapa_Litologico")
    lito_map = get_or_create_lito_map(aprx)

    print("\n[3] Eliminar Mapa_Crono")
    delete_mapa_crono(aprx, fallback_map=lito_map)

    print("\n[4] Recrear Diseño2 (formato Diseño1)")
    lyt2 = get_or_create_layout2(aprx, lyt1, lito_map)

    print("\n[5] Clip unidades crono al tamaño de Fallas_Locales")
    crono_fc = clip_crono_to_fallas(aprx)

    print("\n[6] Capas en Mapa_Litologico")
    configure_lito_map_layers(lito_map, crono_fc, aprx=aprx)

    print("\n[7] Formato layout Diseño2")
    mf = configure_page_and_frames(lyt2, lito_map)
    configure_title(aprx, lyt2)
    configure_legend(lyt2, mf, lito_map)

    print("\n[8] Guardar APRX")
    aprx.save()
    print(f"  OK {APRX_PATH}")

    print("\n[9] Exportar PDF/PNG")
    export_pdf(lyt2)

    print("\n[10] Verificar")
    # Reabrir verificación sobre el aprx en memoria
    verify_isolation(aprx)

    print("\nListo. Diseño1 intacto; Diseño2 -> Mapa_Litologico; sin Mapa_Crono.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        sys.exit(1)
