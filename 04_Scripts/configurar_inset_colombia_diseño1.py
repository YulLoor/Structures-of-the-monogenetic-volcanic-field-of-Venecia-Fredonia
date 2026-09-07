# -*- coding: utf-8 -*-
"""
Reemplaza solo el recuadro pequeno (Marco de mapa 1) de Diseno1 por un
mapa de ubicacion de Colombia con mapa base y recuadro rojo de la zona
Venecia-Fredonia.

No modifica Map_Estructural ni el marco principal.

Ejecutar:
  "C:\\Program Files\\ArcGIS\\Pro\\bin\\Python\\envs\\arcgispro-py3\\python.exe" ^
    04_Scripts\\configurar_inset_colombia_diseno1.py
"""

from __future__ import annotations

import os
import sys
import traceback

import arcpy

ROOT = r"C:\PROYECTO_GIS_VF_Antigraviti"
APRX_PATH = os.path.join(ROOT, "Venecia_Fredonia_Analisis_Estructural.aprx")

MAP_LOCATOR = "Mapa_Ubicacion_Colombia"
LAYOUT1 = "Diseño1"
INSET_NAME = "Marco de mapa 1"
MAIN_MF_NAME = "Marco de mapa"

GDB = os.path.join(
    ROOT,
    "Venecia_Fredonia_Analisis_Estructural",
    "Venecia_Fredonia_Analisis_Estructural.gdb",
)
VOLC_BOX_FC = os.path.join(GDB, "Zona_Volcanes_locator")
CABECERAS_FC = os.path.join(GDB, "Cabeceras_VF")
MUN_FC = os.path.join(GDB, "Municipios_VF")
MUN_LINE_FC = os.path.join(GDB, "Limite_Municipal_VF")

# Cabeceras municipales (WGS84) — tapizan las etiquetas chicas del canvas
CABECERAS = (
    ("Venecia", -75.7507, 5.9564),
    ("Fredonia", -75.6708, 5.9264),
)
# DIVIPOLA Antioquia: Fredonia 05282, Venecia 05861
MUN_CODES = ("05282", "05861")
MUN_SERVICES = (
    "https://portalgis.dane.gov.co/mparcgis/rest/services/Hosted/Serv_Mpio_MGN_2025/FeatureServer/317",
    "https://chamaeleon.supertransporte.gov.co/gisserver/rest/services/Hosted/Limites_Administrativos_Colombia/FeatureServer/0",
    "https://gis.dnp.gov.co/server/rest/services/Hosted/municipios_data/FeatureServer/0",
)

# Municipios Venecia-Fredonia (WGS84) — zoom regional para leer cabeceras
VF_LON = -75.71
VF_LAT = 5.94
# Inset ~2.7 in de ancho; cabeceras Venecia-Fredonia leibles
INSET_SCALE = 220000.0

BASEMAP_CANDIDATES = (
    "Light Gray Canvas",
    "Light Gray Canvas Base",
    "Canvas claro",
    "Lienzo gris claro",
    "Light Gray",
    "Topographic",
    "World Topographic Map",
)


def find_layout1(aprx):
    for lyt in aprx.listLayouts():
        if lyt.name == LAYOUT1 or (
            lyt.name.endswith("1")
            and not lyt.name.endswith("2")
            and "Dise" in lyt.name
        ):
            if abs(lyt.pageWidth - 11.0) < 0.2 and abs(lyt.pageHeight - 8.5) < 0.2:
                return lyt
    for lyt in aprx.listLayouts():
        if lyt.name.endswith("1") and not lyt.name.endswith("2"):
            return lyt
    raise RuntimeError("No se encontro Diseno1")


def get_or_create_locator_map(aprx):
    existing = aprx.listMaps(MAP_LOCATOR)
    if existing:
        amap = existing[0]
        print(f"  OK Mapa existente: {MAP_LOCATOR}")
        return amap
    else:
        amap = aprx.createMap(MAP_LOCATOR, "Map")
        print(f"  OK Creado mapa {MAP_LOCATOR}")

    try:
        names = list(aprx.listBasemaps() or [])
        print(f"  Basemaps disponibles: {names[:12]}")
    except Exception as ex:
        names = []
        print(f"  Aviso listBasemaps: {ex}")

    chosen = None
    lower = [str(n).lower() for n in names]
    for cand in BASEMAP_CANDIDATES:
        for n in names:
            if cand.lower() in str(n).lower() or str(n).lower() in cand.lower():
                chosen = n
                break
        if chosen:
            break
    if chosen is None and names:
        for n in names:
            if "gray" in str(n).lower() or "gris" in str(n).lower() or "canvas" in str(n).lower():
                chosen = n
                break
    if chosen is None and names:
        chosen = names[0]

    if chosen:
        try:
            amap.addBasemap(chosen)
            print(f"  OK Basemap: {chosen}")
        except Exception as ex:
            print(f"  Aviso addBasemap({chosen}): {ex}")
            try:
                amap.addBasemap("Topographic")
                print("  OK Basemap: Topographic (fallback)")
            except Exception as ex2:
                print(f"  ERROR basemap: {ex2}")
    else:
        try:
            amap.addBasemap("Topographic")
            print("  OK Basemap: Topographic")
        except Exception as ex:
            print(f"  ERROR addBasemap: {ex}")

    return amap


def wgs84_to_map_xy(amap, lon, lat):
    """Proyecta un punto WGS84 al SR del mapa (o Web Mercator)."""
    wgs = arcpy.SpatialReference(4326)
    pt = arcpy.PointGeometry(arcpy.Point(lon, lat), wgs)
    sr = None
    try:
        sr = amap.spatialReference
    except Exception:
        sr = None
    if sr is None or getattr(sr, "factoryCode", 0) in (0, None):
        sr = arcpy.SpatialReference(3857)
    try:
        proj = pt.projectAs(sr)
        return proj.centroid.X, proj.centroid.Y, sr
    except Exception:
        # Web Mercator spherical
        import math

        x = lon * 20037508.34 / 180.0
        lat_r = lat * math.pi / 180.0
        y = math.log(math.tan((math.pi / 4.0) + (lat_r / 2.0))) * 6378137.0
        return x, y, arcpy.SpatialReference(3857)


def set_vf_camera(mf, amap, x=None, y=None):
    """Acerca el inset a Venecia-Fredonia para ver municipios y el recuadro."""
    if x is None or y is None:
        x, y, _sr = wgs84_to_map_xy(amap, VF_LON, VF_LAT)
    mf.camera.X = x
    mf.camera.Y = y
    mf.camera.scale = INSET_SCALE
    print(f"  OK Camara VF municipios X={x:.1f} Y={y:.1f} scale 1:{int(INSET_SCALE)}")


def project_extent_envelope(ext, from_sr, to_sr, buffer_m=400.0):
    """Rectangulo del extent, con margen, en to_sr (sin redondear esquinas)."""
    xmin = ext.XMin - buffer_m
    ymin = ext.YMin - buffer_m
    xmax = ext.XMax + buffer_m
    ymax = ext.YMax + buffer_m
    pts = [
        arcpy.Point(xmin, ymin),
        arcpy.Point(xmin, ymax),
        arcpy.Point(xmax, ymax),
        arcpy.Point(xmax, ymin),
        arcpy.Point(xmin, ymin),
    ]
    poly = arcpy.Polygon(arcpy.Array(pts), from_sr)
    if from_sr and to_sr and getattr(from_sr, "factoryCode", None) != getattr(
        to_sr, "factoryCode", None
    ):
        poly = poly.projectAs(to_sr)
    return poly


def _volcano_candidates(path):
    if not path:
        return []
    out = [path]
    if not str(path).lower().endswith(".shp"):
        out.append(path + ".shp")
    return out


def volcanoes_envelope_xy(aprx, loc_map):
    """Centro y envelope de volcanes para el recuadro rojo."""
    src_lyr = None
    src_path = None
    for amap in aprx.listMaps():
        if amap.name == MAP_LOCATOR:
            continue
        for lyr in amap.listLayers():
            n = (lyr.name or "").lower()
            if n == "volcanes" or "cuerpo" in n and "volc" in n:
                src_lyr = lyr
                try:
                    src_path = lyr.dataSource
                except Exception:
                    src_path = None
                break
        if src_lyr:
            break

    loc_sr = None
    try:
        loc_sr = loc_map.spatialReference
    except Exception:
        loc_sr = arcpy.SpatialReference(3857)
    if loc_sr is None or not getattr(loc_sr, "factoryCode", None):
        loc_sr = arcpy.SpatialReference(3857)

    ext = None
    from_sr = None
    used = None
    for cand in _volcano_candidates(src_path):
        if arcpy.Exists(cand):
            used = cand
            break
    if used:
        desc = arcpy.Describe(used)
        ext = desc.extent
        from_sr = desc.spatialReference
        print(f"  Fuente volcanes: {used}")
    elif src_lyr is not None:
        try:
            desc = arcpy.Describe(src_lyr)
            ext = desc.extent
            from_sr = desc.spatialReference
            print(f"  Fuente volcanes: capa {src_lyr.name}")
        except Exception as ex:
            print(f"  Aviso Describe Volcanes: {ex}")
            ext = None
    if ext is None:
        x, y, _ = wgs84_to_map_xy(loc_map, VF_LON, VF_LAT)
        return x, y, None, None

    poly = project_extent_envelope(ext, from_sr, loc_sr, buffer_m=400.0)
    cx = poly.centroid.X
    cy = poly.centroid.Y
    return cx, cy, poly, used


def write_volcano_box(poly, loc_sr):
    arcpy.env.overwriteOutput = True
    sr = loc_sr or arcpy.SpatialReference(3857)
    if arcpy.Exists(VOLC_BOX_FC):
        try:
            arcpy.management.TruncateTable(VOLC_BOX_FC)
        except Exception:
            try:
                arcpy.management.Delete(VOLC_BOX_FC)
            except Exception as ex:
                print(f"  Aviso recuadro existente (lock): {ex}")
                return VOLC_BOX_FC
    if not arcpy.Exists(VOLC_BOX_FC):
        arcpy.management.CreateFeatureclass(
            os.path.dirname(VOLC_BOX_FC),
            os.path.basename(VOLC_BOX_FC),
            "POLYGON",
            spatial_reference=sr,
        )
    with arcpy.da.InsertCursor(VOLC_BOX_FC, ["SHAPE@"]) as cur:
        cur.insertRow([poly])
    print(f"  OK Recuadro volcanes: {VOLC_BOX_FC}")
    return VOLC_BOX_FC


def style_red_box_layer(lyr):
    cim = lyr.getDefinition("V3")
    stroke_color = arcpy.cim.CreateCIMObjectFromClassName("CIMRGBColor", "V3")
    stroke_color.values = [255.0, 0.0, 0.0, 100.0]
    fill_color = arcpy.cim.CreateCIMObjectFromClassName("CIMRGBColor", "V3")
    fill_color.values = [255.0, 0.0, 0.0, 10.0]
    stroke = arcpy.cim.CreateCIMObjectFromClassName("CIMSolidStroke", "V3")
    stroke.width = 2.5
    stroke.color = stroke_color
    stroke.enable = True
    fill = arcpy.cim.CreateCIMObjectFromClassName("CIMSolidFill", "V3")
    fill.color = fill_color
    fill.enable = True
    poly = arcpy.cim.CreateCIMObjectFromClassName("CIMPolygonSymbol", "V3")
    poly.symbolLayers = [stroke, fill]
    ref = arcpy.cim.CreateCIMObjectFromClassName("CIMSymbolReference", "V3")
    ref.symbol = poly
    renderer = arcpy.cim.CreateCIMObjectFromClassName("CIMSimpleRenderer", "V3")
    renderer.symbol = ref
    cim.renderer = renderer
    lyr.setDefinition(cim)
    lyr.visible = True
    try:
        lyr.name = "Zona volcanes"
    except Exception:
        pass


def add_volcano_box_to_locator(amap, poly):
    loc_sr = None
    try:
        loc_sr = amap.spatialReference
    except Exception:
        loc_sr = None
    fc = write_volcano_box(poly, loc_sr)
    for lyr in list(amap.listLayers()):
        if lyr.name in ("Zona volcanes", "Zona_Volcanes_locator"):
            try:
                amap.removeLayer(lyr)
            except Exception:
                pass
    lyr = amap.addDataFromPath(fc)
    style_red_box_layer(lyr)
    try:
        top = amap.listLayers()[0]
        if lyr != top:
            amap.moveLayer(top, lyr, "BEFORE")
    except Exception:
        pass
    print("  OK Capa recuadro rojo (volcanes) en locator")


def _rgb(r, g, b, a=100):
    c = arcpy.cim.CreateCIMObjectFromClassName("CIMRGBColor", "V3")
    c.values = [float(r), float(g), float(b), float(a)]
    return c


def style_green_volcanoes_layer(lyr):
    """Mismo verde forestal del mapa principal; sin etiquetas en el inset."""
    fill = arcpy.cim.CreateCIMObjectFromClassName("CIMSolidFill", "V3")
    fill.color = _rgb(34, 139, 34, 85)
    fill.enable = True
    stroke = arcpy.cim.CreateCIMObjectFromClassName("CIMSolidStroke", "V3")
    stroke.color = _rgb(0, 100, 0, 100)
    stroke.width = 1.2
    stroke.enable = True
    poly = arcpy.cim.CreateCIMObjectFromClassName("CIMPolygonSymbol", "V3")
    poly.symbolLayers = [stroke, fill]
    ref = arcpy.cim.CreateCIMObjectFromClassName("CIMSymbolReference", "V3")
    ref.symbol = poly
    renderer = arcpy.cim.CreateCIMObjectFromClassName("CIMSimpleRenderer", "V3")
    renderer.symbol = ref
    renderer.heading = "Cuerpos Volcánicos"
    cim = lyr.getDefinition("V3")
    cim.renderer = renderer
    for lc in cim.labelClasses or []:
        lc.visibility = False
    lyr.setDefinition(cim)
    lyr.visible = True
    try:
        lyr.showLabels = False
    except Exception:
        pass
    try:
        lyr.name = "Volcanes"
    except Exception:
        pass


def add_green_volcanoes_to_locator(amap, src_path):
    """Copia independiente de volcanes (verde) al mapa pequeno."""
    if not src_path or not arcpy.Exists(src_path):
        print("  Aviso: no hay shapefile de volcanes para el inset")
        return
    for lyr in list(amap.listLayers()):
        n = lyr.name or ""
        if n == "Volcanes" or n.lower().startswith("volcanes"):
            try:
                amap.removeLayer(lyr)
            except Exception:
                pass
    lyr = amap.addDataFromPath(src_path)
    style_green_volcanoes_layer(lyr)
    try:
        red = None
        for L in amap.listLayers():
            if L.name in ("Zona volcanes", "Zona_Volcanes_locator"):
                red = L
                break
        if red is not None:
            amap.moveLayer(red, lyr, "AFTER")
        else:
            top = amap.listLayers()[0]
            if lyr != top:
                amap.moveLayer(top, lyr, "BEFORE")
    except Exception as ex:
        print(f"  Aviso orden capas volcanes: {ex}")
    print("  OK Volcanes verdes en el mapa pequeno")


def _recreate_fc(path, geom_type, sr):
    arcpy.env.overwriteOutput = True
    if arcpy.Exists(path):
        try:
            arcpy.management.TruncateTable(path)
            return path
        except Exception:
            try:
                arcpy.management.Delete(path)
            except Exception as ex:
                print(f"  Aviso lock {os.path.basename(path)}: {ex}")
                return path
    arcpy.management.CreateFeatureclass(
        os.path.dirname(path),
        os.path.basename(path),
        geom_type,
        spatial_reference=sr,
    )
    return path


def hide_basemap_reference(amap):
    """Apaga la capa Reference del canvas (limites grises + labels chicas)."""
    hid = 0
    for lyr in amap.listLayers():
        n = (lyr.name or "").lower()
        if any(k in n for k in ("reference", "referencia", "hybrid reference")):
            try:
                lyr.visible = False
                hid += 1
                print(f"  OK Oculta basemap: {lyr.name}")
            except Exception:
                pass
        try:
            if lyr.isGroupLayer:
                for sub in lyr.listLayers():
                    sn = (sub.name or "").lower()
                    if any(k in sn for k in ("reference", "referencia")):
                        sub.visible = False
                        hid += 1
                        print(f"  OK Oculta basemap: {sub.name}")
        except Exception:
            pass
    if hid == 0:
        print("  Aviso: no se hallo capa Reference del canvas")


def write_cabeceras_fc(amap):
    loc_sr = None
    try:
        loc_sr = amap.spatialReference
    except Exception:
        loc_sr = None
    if loc_sr is None or not getattr(loc_sr, "factoryCode", None):
        loc_sr = arcpy.SpatialReference(3857)
    wgs = arcpy.SpatialReference(4326)
    path = _recreate_fc(CABECERAS_FC, "POINT", loc_sr)
    names = [f.name for f in arcpy.ListFields(path)]
    if "Nombre" not in names:
        arcpy.management.AddField(path, "Nombre", "TEXT", field_length=40)
    try:
        arcpy.management.TruncateTable(path)
    except Exception:
        pass
    with arcpy.da.InsertCursor(path, ["SHAPE@", "Nombre"]) as cur:
        for nombre, lon, lat in CABECERAS:
            geom = arcpy.PointGeometry(arcpy.Point(lon, lat), wgs).projectAs(loc_sr)
            cur.insertRow([geom, nombre])
    print(f"  OK Cabeceras: {path}")
    return path


def style_cabeceras_layer(lyr):
    """Punto invisible + etiqueta grande con halo."""
    fill = arcpy.cim.CreateCIMObjectFromClassName("CIMSolidFill", "V3")
    fill.color = _rgb(0, 0, 0, 0)
    fill.enable = True
    stroke = arcpy.cim.CreateCIMObjectFromClassName("CIMSolidStroke", "V3")
    stroke.color = _rgb(0, 0, 0, 0)
    stroke.width = 0
    stroke.enable = False
    poly = arcpy.cim.CreateCIMObjectFromClassName("CIMPolygonSymbol", "V3")
    poly.symbolLayers = [stroke, fill]
    import math

    pts = [
        arcpy.Point(math.cos(2 * math.pi * i / 16.0), math.sin(2 * math.pi * i / 16.0))
        for i in range(17)
    ]
    graphic = arcpy.cim.CreateCIMObjectFromClassName("CIMMarkerGraphic", "V3")
    graphic.symbol = poly
    graphic.geometry = arcpy.Polygon(arcpy.Array(pts))
    vm = arcpy.cim.CreateCIMObjectFromClassName("CIMVectorMarker", "V3")
    vm.size = 1.0
    vm.enable = True
    vm.frame = arcpy.Extent(-1, -1, 1, 1)
    vm.markerGraphics = [graphic]
    pt = arcpy.cim.CreateCIMObjectFromClassName("CIMPointSymbol", "V3")
    pt.symbolLayers = [vm]
    ref = arcpy.cim.CreateCIMObjectFromClassName("CIMSymbolReference", "V3")
    ref.symbol = pt
    rend = arcpy.cim.CreateCIMObjectFromClassName("CIMSimpleRenderer", "V3")
    rend.symbol = ref
    rend.label = ""

    cim = lyr.getDefinition("V3")
    cim.renderer = rend
    cim.minScale = 0
    cim.maxScale = 0
    lyr.setDefinition(cim)

    lyr.showLabels = True
    cim = lyr.getDefinition("V3")
    if not cim.labelClasses:
        lc = arcpy.cim.CreateCIMObjectFromClassName("CIMLabelClass", "V3")
        cim.labelClasses = [lc]
    lc = cim.labelClasses[0]
    lc.visibility = True
    lc.name = "Nombre"
    lc.expressionEngine = "Python"
    lc.expression = "[Nombre]"
    try:
        lc.minScale = 0
        lc.maxScale = 0
    except Exception:
        pass
    ts = lc.textSymbol.symbol
    ts.height = 18.0
    ts.fontFamilyName = "Arial"
    ts.fontStyleName = "Bold"
    for sl in getattr(ts, "symbolLayers", []) or []:
        if type(sl).__name__ == "CIMSolidFill":
            sl.color = _rgb(0, 0, 0, 100)
    halo_fill = arcpy.cim.CreateCIMObjectFromClassName("CIMSolidFill", "V3")
    halo_fill.color = _rgb(255, 255, 255, 100)
    halo = arcpy.cim.CreateCIMObjectFromClassName("CIMPolygonSymbol", "V3")
    halo.symbolLayers = [halo_fill]
    try:
        ts.haloSize = 1.8
        ts.haloSymbol = halo
    except Exception:
        pass
    lyr.setDefinition(cim)
    lyr.showLabels = True
    lyr.visible = True
    try:
        lyr.name = "Cabeceras VF"
    except Exception:
        pass
    print("  OK Etiquetas Venecia / Fredonia 18 pt")


def add_cabeceras_to_locator(amap):
    fc = write_cabeceras_fc(amap)
    for lyr in list(amap.listLayers()):
        if lyr.name in ("Cabeceras VF", "Cabeceras_VF"):
            try:
                amap.removeLayer(lyr)
            except Exception:
                pass
    lyr = amap.addDataFromPath(fc)
    style_cabeceras_layer(lyr)
    try:
        top = amap.listLayers()[0]
        if lyr != top:
            amap.moveLayer(top, lyr, "BEFORE")
    except Exception:
        pass


def download_municipios_fc(out_path, loc_sr):
    if arcpy.Exists(out_path):
        try:
            n = int(arcpy.management.GetCount(out_path)[0])
            if n >= 2:
                print(f"  OK Municipios VF ya en GDB ({n})")
                return out_path
        except Exception:
            pass
    where = "mpio_cdpmp IN ('05282','05861') OR MPIO_CDPMP IN ('05282','05861')"
    arcpy.env.overwriteOutput = True
    tmp = os.path.join(arcpy.env.scratchGDB, "mpio_vf_dl")
    for url in MUN_SERVICES:
        try:
            if arcpy.Exists(tmp):
                try:
                    arcpy.management.Delete(tmp)
                except Exception:
                    pass
            print(f"  Consulta municipios: {url}")
            arcpy.conversion.ExportFeatures(url, tmp, where_clause=where)
            n = int(arcpy.management.GetCount(tmp)[0])
            if n < 2:
                print(f"  Aviso: {n} municipios, se prueba otro servicio")
                continue
            if arcpy.Exists(out_path):
                try:
                    arcpy.management.Delete(out_path)
                except Exception:
                    pass
            arcpy.management.Project(tmp, out_path, loc_sr)
            try:
                arcpy.management.Delete(tmp)
            except Exception:
                pass
            print(f"  OK Municipios VF ({n}): {out_path}")
            return out_path
        except Exception as ex:
            print(f"  Aviso servicio municipios: {ex}")
    return None


def write_fallback_limite(out_path, loc_sr):
    """Linea N-S aproximada entre Venecia (oeste) y Fredonia (este)."""
    wgs = arcpy.SpatialReference(4326)
    path = _recreate_fc(out_path, "POLYLINE", loc_sr)
    pts_wgs = [(-75.720, 6.02), (-75.718, 5.97), (-75.712, 5.94), (-75.708, 5.88)]
    arr = arcpy.Array([arcpy.Point(lon, lat) for lon, lat in pts_wgs])
    line = arcpy.Polyline(arr, wgs).projectAs(loc_sr)
    try:
        arcpy.management.TruncateTable(path)
    except Exception:
        pass
    with arcpy.da.InsertCursor(path, ["SHAPE@"]) as cur:
        cur.insertRow([line])
    print("  OK Limite municipal aproximado (fallback)")
    return path


def style_municipios_outline(lyr, is_line=False):
    stroke = arcpy.cim.CreateCIMObjectFromClassName("CIMSolidStroke", "V3")
    stroke.color = _rgb(0, 0, 0, 100)
    stroke.width = 2.4
    stroke.enable = True
    if is_line:
        ls = arcpy.cim.CreateCIMObjectFromClassName("CIMLineSymbol", "V3")
        ls.symbolLayers = [stroke]
        ref = arcpy.cim.CreateCIMObjectFromClassName("CIMSymbolReference", "V3")
        ref.symbol = ls
    else:
        fill = arcpy.cim.CreateCIMObjectFromClassName("CIMSolidFill", "V3")
        fill.color = _rgb(0, 0, 0, 0)
        fill.enable = True
        poly = arcpy.cim.CreateCIMObjectFromClassName("CIMPolygonSymbol", "V3")
        poly.symbolLayers = [stroke, fill]
        ref = arcpy.cim.CreateCIMObjectFromClassName("CIMSymbolReference", "V3")
        ref.symbol = poly
    rend = arcpy.cim.CreateCIMObjectFromClassName("CIMSimpleRenderer", "V3")
    rend.symbol = ref
    cim = lyr.getDefinition("V3")
    cim.renderer = rend
    for lc in cim.labelClasses or []:
        lc.visibility = False
    lyr.setDefinition(cim)
    lyr.visible = True
    try:
        lyr.showLabels = False
    except Exception:
        pass
    try:
        lyr.name = "Limite municipal VF"
    except Exception:
        pass
    print("  OK Limite municipal negro")


def add_municipios_to_locator(amap):
    loc_sr = None
    try:
        loc_sr = amap.spatialReference
    except Exception:
        loc_sr = None
    if loc_sr is None or not getattr(loc_sr, "factoryCode", None):
        loc_sr = arcpy.SpatialReference(3857)
    fc = download_municipios_fc(MUN_FC, loc_sr)
    is_line = False
    if fc is None:
        fc = write_fallback_limite(MUN_LINE_FC, loc_sr)
        is_line = True
    else:
        desc = arcpy.Describe(fc)
        if desc.shapeType.lower() == "polygon":
            arcpy.env.overwriteOutput = True
            try:
                if arcpy.Exists(MUN_LINE_FC):
                    arcpy.management.Delete(MUN_LINE_FC)
            except Exception:
                pass
            arcpy.management.PolygonToLine(fc, MUN_LINE_FC, "IDENTIFY_NEIGHBORS")
            fc = MUN_LINE_FC
            is_line = True
            print("  OK Poligonos a lineas de limite")
        else:
            is_line = True
    for lyr in list(amap.listLayers()):
        if lyr.name in ("Limite municipal VF", "Municipios_VF", "Limite_Municipal_VF"):
            try:
                amap.removeLayer(lyr)
            except Exception:
                pass
    lyr = amap.addDataFromPath(fc)
    style_municipios_outline(lyr, is_line=is_line)
    try:
        cab = None
        for L in amap.listLayers():
            if L.name in ("Cabeceras VF", "Cabeceras_VF"):
                cab = L
                break
        if cab is not None:
            amap.moveLayer(cab, lyr, "AFTER")
        else:
            top = amap.listLayers()[0]
            if lyr != top:
                amap.moveLayer(top, lyr, "BEFORE")
    except Exception as ex:
        print(f"  Aviso orden limite: {ex}")


def strip_inset_grids(inset):
    try:
        inset.removeGrids("*")
        print("  OK Grilla del inset eliminada")
    except Exception as ex:
        print(f"  Aviso removeGrids inset: {ex}")


def red_extent_symbol():
    stroke_color = arcpy.cim.CreateCIMObjectFromClassName("CIMRGBColor", "V3")
    stroke_color.values = [255.0, 0.0, 0.0, 100.0]
    fill_color = arcpy.cim.CreateCIMObjectFromClassName("CIMRGBColor", "V3")
    fill_color.values = [255.0, 0.0, 0.0, 25.0]
    stroke = arcpy.cim.CreateCIMObjectFromClassName("CIMSolidStroke", "V3")
    stroke.width = 1.5
    stroke.color = stroke_color
    stroke.enable = True
    fill = arcpy.cim.CreateCIMObjectFromClassName("CIMSolidFill", "V3")
    fill.color = fill_color
    fill.enable = True
    symbol = arcpy.cim.CreateCIMObjectFromClassName("CIMPolygonSymbol", "V3")
    symbol.symbolLayers = [stroke, fill]
    symbol_ref = arcpy.cim.CreateCIMObjectFromClassName("CIMSymbolReference", "V3")
    symbol_ref.symbol = symbol
    return symbol_ref


def clear_extent_indicators(lyt, inset):
    lyt_cim = lyt.getDefinition("V3")
    for elm in lyt_cim.elements:
        if getattr(elm, "name", None) != inset.name:
            continue
        elm.extentIndicators = []
        lyt.setDefinition(lyt_cim)
        print("  OK Indicadores de extension anteriores eliminados")
        return


def add_red_extent_indicator(lyt, main_mf, inset):
    lyt_cim = lyt.getDefinition("V3")
    ei_cim = arcpy.cim.CreateCIMObjectFromClassName("CIMExtentIndicator", "V3")
    ei_cim.sourceMapFrame = main_mf.name
    ei_cim.extentIndicatorType = "Frame"
    ei_cim.isVisible = True
    ei_cim.name = "Zona_estudio_VF"
    ei_cim.symbol = red_extent_symbol()

    found = False
    for elm in lyt_cim.elements:
        if getattr(elm, "name", None) != inset.name:
            continue
        if not getattr(elm, "extentIndicators", None):
            elm.extentIndicators = []
        # Quitar indicadores previos para no duplicar
        keep = []
        for ei in elm.extentIndicators:
            n = getattr(ei, "name", "")
            if n not in ("Zona_estudio_VF", "extent_indicator"):
                keep.append(ei)
        elm.extentIndicators = keep
        elm.extentIndicators.insert(0, ei_cim)
        found = True
        break

    if not found:
        raise RuntimeError(f"No se hallo CIM del inset {inset.name!r}")

    lyt.setDefinition(lyt_cim)
    print("  OK Extent indicator rojo (Venecia-Fredonia)")


def main():
    print("=" * 60)
    print("Diseno1 — inset municipios VF + recuadro rojo volcanes")
    print("=" * 60)

    if not os.path.exists(APRX_PATH):
        raise FileNotFoundError(APRX_PATH)

    aprx = arcpy.mp.ArcGISProject(APRX_PATH)
    lyt = find_layout1(aprx)
    print(f"Layout: {lyt.name!r}")

    print("\n[1] Mapa de ubicacion Colombia")
    loc_map = get_or_create_locator_map(aprx)

    print("\n[2] Reasignar Marco de mapa 1 (municipios VF)")
    mains = lyt.listElements("MAPFRAME_ELEMENT", MAIN_MF_NAME)
    insets = lyt.listElements("MAPFRAME_ELEMENT", INSET_NAME)
    if not mains:
        mains = [
            e
            for e in lyt.listElements("MAPFRAME_ELEMENT")
            if e.name == MAIN_MF_NAME or (INSET_NAME not in e.name)
        ]
    if not insets:
        raise RuntimeError("No existe Marco de mapa 1")
    main_mf = mains[0] if mains else None
    if main_mf is None:
        raise RuntimeError("No existe Marco de mapa principal")
    inset = insets[0]
    inset.map = loc_map

    cx, cy, volc_poly, volc_src = volcanoes_envelope_xy(aprx, loc_map)
    set_vf_camera(inset, loc_map, x=cx, y=cy)
    strip_inset_grids(inset)

    print("\n[3] Volcanes verdes + recuadro rojo")
    clear_extent_indicators(lyt, inset)
    if volc_src:
        add_green_volcanoes_to_locator(loc_map, volc_src)
    has_red = any(
        L.name in ("Zona volcanes", "Zona_Volcanes_locator")
        for L in loc_map.listLayers()
    )
    if volc_poly is not None and not has_red:
        try:
            add_volcano_box_to_locator(loc_map, volc_poly)
        except Exception as ex:
            print(f"  Aviso recuadro rojo: {ex}")
    elif has_red:
        print("  OK Recuadro rojo ya presente")
    else:
        add_red_extent_indicator(lyt, main_mf, inset)

    print("\n[4] Etiquetas Venecia/Fredonia + limite municipal negro")
    hide_basemap_reference(loc_map)
    add_cabeceras_to_locator(loc_map)
    add_municipios_to_locator(loc_map)

    print("\n[5] Guardar APRX")
    try:
        aprx.save()
        print(f"  OK {APRX_PATH}")
    except Exception as ex:
        print(f"  ERROR al guardar: {ex}")
        print("  Cierra ArcGIS Pro SIN guardar y vuelve a ejecutar el script.")
        raise

    print("\nVerificacion:")
    print(f"  Principal {main_mf.name} -> {main_mf.map.name if main_mf.map else None}")
    print(f"  Inset {inset.name} -> {inset.map.name if inset.map else None}")
    print(f"  Inset scale {inset.camera.scale}")
    assert inset.map and inset.map.name == MAP_LOCATOR
    assert main_mf.map and main_mf.map.name != MAP_LOCATOR

    print("\nListo. Si Pro tenia el proyecto abierto, cierra SIN guardar y reabre.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        sys.exit(1)
