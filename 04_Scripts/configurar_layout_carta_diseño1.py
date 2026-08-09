# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import sys
import traceback

import arcpy

# ---------------------------------------------------------------------------
# Rutas y constantes
# ---------------------------------------------------------------------------
ROOT = r"C:\PROYECTO_GIS_VF_Antigraviti"
APRX_PATH = os.path.join(ROOT, "Venecia_Fredonia_Analisis_Estructural.aprx")
PDF_PATH = os.path.join(ROOT, "05_Salidas", "Mapa_Estructural_VF_Carta.pdf")

SCALE = 60000.0
INSET_SCALE = 400000.0
MAP_CENTER_X = 4697287.0
MAP_CENTER_Y = 2213314.0

# Letter landscape (pulgadas) — composición tipo ejemplo
PAGE_W = 11.0
PAGE_H = 8.5
MARGIN = 0.30
RIGHT_COL_W = 2.70  # inset + leyenda


FALLAS_CINEMATICA = [
    ("cauca-almaguer", "Rumbo Dextral / Transpresiva"),
    ("mistrat", "Rumbo Dextral"),
    ("cascajosa", "Normal / Transcurrente local"),
    ("san jer", "Inversa / Rumbo Dextral"),
    ("piede", "Inversa / Cabalgamiento"),
]

SCALE_TEXT = "Escala 1:60000"

APA_LOPEZ_2006 = "López et al. (2006)"


# Utilidades CIM
def rgb(r, g, b, a=100):
    c = arcpy.cim.CreateCIMObjectFromClassName("CIMRGBColor", "V3")
    c.values = [float(r), float(g), float(b), float(a)]
    return c


def white_halo_symbol(halo_pt=1.5):
    fill = arcpy.cim.CreateCIMObjectFromClassName("CIMSolidFill", "V3")
    fill.color = rgb(255, 255, 255, 100)
    poly = arcpy.cim.CreateCIMObjectFromClassName("CIMPolygonSymbol", "V3")
    poly.symbolLayers = [fill]
    return poly


def solid_stroke(width_pt, color_rgb=(0, 0, 0), dash_template=None):
    stroke = arcpy.cim.CreateCIMObjectFromClassName("CIMSolidStroke", "V3")
    stroke.width = float(width_pt)
    stroke.color = rgb(*color_rgb)
    stroke.capStyle = "Round"
    stroke.joinStyle = "Round"
    stroke.enable = True
    if dash_template:
        dash = arcpy.cim.CreateCIMObjectFromClassName(
            "CIMGeometricEffectDashes", "V3"
        )
        dash.dashTemplate = list(dash_template)
        dash.lineDashEnding = "NoConstraint"
        dash.controlPointEnding = "NoConstraint"
        stroke.effects = [dash]
    else:
        stroke.effects = []
    return stroke


def along_line_placement(spacing_pt=14.0, offset=0.0, angle_to_line=True):
    place = arcpy.cim.CreateCIMObjectFromClassName(
        "CIMMarkerPlacementAlongLineSameSize", "V3"
    )
    place.placementTemplate = [float(spacing_pt)]
    place.angleToLine = bool(angle_to_line)
    place.offset = float(offset)
    place.endings = "WithMarkers"
    place.placePerPart = True
    return place


def character_marker_along_line(
    character_index,
    size_pt=7.0,
    spacing_pt=14.0,
    offset=0.0,
    font_family="Segoe UI Symbol",
    color_rgb=(0, 0, 0),
    rotation=0.0,
):
    
    fill = arcpy.cim.CreateCIMObjectFromClassName("CIMSolidFill", "V3")
    fill.color = rgb(*color_rgb)
    poly = arcpy.cim.CreateCIMObjectFromClassName("CIMPolygonSymbol", "V3")
    poly.symbolLayers = [fill]
    poly_ref = arcpy.cim.CreateCIMObjectFromClassName("CIMSymbolReference", "V3")
    poly_ref.symbol = poly

    cm = arcpy.cim.CreateCIMObjectFromClassName("CIMCharacterMarker", "V3")
    cm.fontFamilyName = font_family
    cm.fontStyleName = "Regular"
    cm.characterIndex = int(character_index)
    cm.size = float(size_pt)
    cm.rotation = float(rotation)
    cm.enable = True
    cm.symbol = poly_ref
    cm.markerPlacement = along_line_placement(spacing_pt, offset, True)
    return cm


def vector_triangle_marker(size_pt=8.0, spacing_pt=16.0, offset=3.5):
    """Triángulos de cabalgamiento/inversa a un lado de la línea."""
    # Triángulo equilátero apuntando "hacia fuera" (arriba local)
    tri = arcpy.cim.CreateCIMObjectFromClassName("CIMVectorMarker", "V3")
    tri.size = float(size_pt)
    tri.enable = True
    tri.frameXMin = -5
    tri.frameYMin = -5
    tri.frameXMax = 5
    tri.frameYMax = 5
    try:
        # Envelope-like frame attributes vary by version; ignore if absent
        tri.frame = None
    except Exception:
        pass

    fill = arcpy.cim.CreateCIMObjectFromClassName("CIMSolidFill", "V3")
    fill.color = rgb(0, 0, 0, 100)
    outline = arcpy.cim.CreateCIMObjectFromClassName("CIMSolidStroke", "V3")
    outline.color = rgb(0, 0, 0, 100)
    outline.width = 0.2
    poly_sym = arcpy.cim.CreateCIMObjectFromClassName("CIMPolygonSymbol", "V3")
    poly_sym.symbolLayers = [outline, fill]

    graphic = arcpy.cim.CreateCIMObjectFromClassName("CIMMarkerGraphic", "V3")
    # Geometría del triángulo en unidades del marco del marker
    pts = arcpy.Array(
        [
            arcpy.Point(0, 4.5),
            arcpy.Point(-4.0, -3.5),
            arcpy.Point(4.0, -3.5),
            arcpy.Point(0, 4.5),
        ]
    )
    graphic.geometry = arcpy.Polygon(pts)
    sym_ref = arcpy.cim.CreateCIMObjectFromClassName("CIMSymbolReference", "V3")
    sym_ref.symbol = poly_sym
    graphic.symbol = sym_ref
    tri.markerGraphics = [graphic]
    tri.markerPlacement = along_line_placement(spacing_pt, offset, True)
    return tri


def vector_tick_marker(size_pt=7.0, spacing_pt=12.0, offset=0.0):
    """Tics perpendiculares de falla normal."""
    tick = arcpy.cim.CreateCIMObjectFromClassName("CIMVectorMarker", "V3")
    tick.size = float(size_pt)
    tick.enable = True

    stroke = arcpy.cim.CreateCIMObjectFromClassName("CIMSolidStroke", "V3")
    stroke.color = rgb(0, 0, 0, 100)
    stroke.width = 1.2
    line_sym = arcpy.cim.CreateCIMObjectFromClassName("CIMLineSymbol", "V3")
    line_sym.symbolLayers = [stroke]

    graphic = arcpy.cim.CreateCIMObjectFromClassName("CIMMarkerGraphic", "V3")
    graphic.geometry = arcpy.Polyline(
        arcpy.Array([arcpy.Point(0, -4.5), arcpy.Point(0, 4.5)])
    )
    sym_ref = arcpy.cim.CreateCIMObjectFromClassName("CIMSymbolReference", "V3")
    sym_ref.symbol = line_sym
    graphic.symbol = sym_ref
    tick.markerGraphics = [graphic]
    tick.markerPlacement = along_line_placement(spacing_pt, offset, True)
    return tick


def build_line_symbol(layers):
    line = arcpy.cim.CreateCIMObjectFromClassName("CIMLineSymbol", "V3")
    line.symbolLayers = list(layers)
    ref = arcpy.cim.CreateCIMObjectFromClassName("CIMSymbolReference", "V3")
    ref.symbol = line
    return ref


def set_stroke(symbol_ref, width_pt, color_rgb, dash_template=None):
    sym = symbol_ref.symbol
    for layer in sym.symbolLayers:
        if type(layer).__name__ != "CIMSolidStroke":
            continue
        layer.width = float(width_pt)
        layer.color = rgb(*color_rgb)
        if dash_template:
            dash = arcpy.cim.CreateCIMObjectFromClassName(
                "CIMGeometricEffectDashes", "V3"
            )
            dash.dashTemplate = list(dash_template)
            dash.lineDashEnding = "NoConstraint"
            dash.controlPointEnding = "NoConstraint"
            layer.effects = [dash]
        else:
            keep = [
                e
                for e in (layer.effects or [])
                if type(e).__name__ != "CIMGeometricEffectDashes"
            ]
            layer.effects = keep
        break


def class_key(uv_class):
    label = (getattr(uv_class, "label", None) or "").strip().lower()
    if label:
        return label
    try:
        vals = uv_class.values
        if vals:
            return str(vals[0].fieldValues[0]).strip().lower()
    except Exception:
        pass
    return ""


def configure_labels(lyr, expression, size_pt, bold=True, halo_pt=1.5, engine="Arcade"):
    lyr.showLabels = True
    cim = lyr.getDefinition("V3")
    if not cim.labelClasses:
        return
    for lc in cim.labelClasses:
        lc.visibility = True
        lc.expression = expression
        try:
            lc.expressionEngine = engine
        except Exception:
            pass
        ts = lc.textSymbol.symbol
        ts.height = float(size_pt)
        ts.fontFamilyName = "Arial"
        ts.fontStyleName = "Bold" if bold else "Regular"
        ts.haloSize = float(halo_pt)
        ts.haloSymbol = white_halo_symbol(halo_pt)
        for sl in getattr(ts, "symbolLayers", []) or []:
            if type(sl).__name__ == "CIMSolidFill":
                sl.color = rgb(0, 0, 0, 100)
    try:
        cim.labelWeight = "High"
    except Exception:
        pass
    lyr.setDefinition(cim)


def find_layout(aprx, suffix="1"):
    layouts = aprx.listLayouts()
    for lyt in layouts:
        if lyt.name.endswith(suffix) and len(lyt.name) > 1:
            return lyt
    if len(layouts) >= 2:
        return layouts[1]
    raise RuntimeError("No se encontró el layout Diseño1")


def find_layer(amap, *candidates):
    for name in candidates:
        layers = amap.listLayers(name)
        if layers:
            return layers[0]
    raise RuntimeError(f"Capa no encontrada: {candidates}")



# Simbología
def sgc_symbol_for_fault(tipo_key, dashed=False):
    """
    Construye símbolo lineal tipo SGC:
    - rumbo: línea + flechas
    - inversa/cabalgamiento: línea + triángulos
    - normal: línea + tics
    - genérica: línea negra 2 pt
    """
    dash = [1.5, 1.0] if dashed else None
    stroke = solid_stroke(2.0, (0, 0, 0), dash)
    layers = []

    if "inversa" in tipo_key or "cabalgamiento" in tipo_key:
        layers.append(vector_triangle_marker(8.0, 16.0, 3.5))
    elif "normal" in tipo_key:
        layers.append(vector_tick_marker(7.0, 12.0, 0.0))
    elif "rumbo" in tipo_key or "dextral" in tipo_key or "sinestral" in tipo_key:
        # Flecha (▲/→) — índice 9658 ► o 10148 ➜; usar 9654 ▶
        layers.append(
            character_marker_along_line(
                9654, size_pt=6.5, spacing_pt=18.0, offset=0.0
            )
        )
    # Stroke debajo de markers (en CIM el orden: primero = encima)
    layers.append(stroke)
    return build_line_symbol(layers)


def make_uv_value(field_value):
    uv = arcpy.cim.CreateCIMObjectFromClassName("CIMUniqueValue", "V3")
    uv.fieldValues = [field_value]
    return uv


def make_uv_class(label, field_value, symbol_ref, visible=True, description=""):
    cls = arcpy.cim.CreateCIMObjectFromClassName("CIMUniqueValueClass", "V3")
    cls.label = label
    cls.description = description or ""
    cls.visible = visible
    cls.editable = True
    cls.symbol = symbol_ref
    cls.values = [make_uv_value(field_value)]
    return cls


def update_lineamientos(lyr):
    cim = lyr.getDefinition("V3")
    rules = {
        "verdadero": (2.0, (230, 0, 0), None),
        "inferido": (1.8, (255, 127, 0), [5.0, 5.0]),
        "literatura": (2.2, (0, 77, 168), None),
    }
    for grp in cim.renderer.groups:
        try:
            grp.heading = "Lineamientos geológicos"
        except Exception:
            pass
        for cls in grp.classes:
            key = class_key(cls)
            matched = None
            for k, v in rules.items():
                if k in key:
                    matched = v
                    break
            if matched:
                w, col, dash = matched
                set_stroke(cls.symbol, w, col, dash)
            if "inferido" in key:
                cls.label = "Lineamiento inferido"
                cls.description = ""
            elif "literatura" in key:
                cls.label = f"Lineamiento por literatura — {APA_LOPEZ_2006}"
                cls.description = ""
            elif "verdadero" in key:
                cls.label = "Lineamiento verdadero (interpretado)"
                cls.description = ""
    lyr.setDefinition(cim)
    lyr.showLabels = False
    print("  OK Lineamientos (verdadero / inferido / literatura APA)")


def update_fallas(lyr):
    """Leyenda por tipo cinemático dominante (no por nombre de falla)."""
    gdb = os.path.join(
        ROOT,
        "Venecia_Fredonia_Analisis_Estructural",
        "Venecia_Fredonia_Analisis_Estructural.gdb",
        "Fallas_Locales",
    )
    # Resolver NombreFalla exacto en GDB por clave
    found = {}  # key -> exact name
    if arcpy.Exists(gdb):
        with arcpy.da.SearchCursor(gdb, ["NombreFalla"]) as cur:
            for (n,) in cur:
                if not n or not str(n).strip():
                    continue
                name = str(n).strip()
                nl = name.lower()
                for wk, _label in FALLAS_CINEMATICA:
                    if wk in nl and wk not in found:
                        found[wk] = name

    cim = lyr.getDefinition("V3")
    renderer = arcpy.cim.CreateCIMObjectFromClassName("CIMUniqueValueRenderer", "V3")
    renderer.fields = ["NombreFalla"]
    renderer.useDefaultSymbol = True
    renderer.isDefaultSymbolVisible = True
    renderer.defaultLabel = "Otras fallas"
    renderer.defaultSymbol = build_line_symbol([solid_stroke(2.0, (0, 0, 0), None)])

    group = arcpy.cim.CreateCIMObjectFromClassName("CIMUniqueValueGroup", "V3")
    group.heading = "Tipo cinemático dominante"
    classes = []
    labels_ok = []
    for wk, cinematica in FALLAS_CINEMATICA:
        if wk not in found:
            continue
        name = found[wk]
        classes.append(
            make_uv_class(
                cinematica,
                name,
                build_line_symbol([solid_stroke(2.0, (0, 0, 0), None)]),
            )
        )
        labels_ok.append(f"{name} -> {cinematica}")
    group.classes = classes
    renderer.groups = [group]
    cim.renderer = renderer
    lyr.setDefinition(cim)
    configure_labels(lyr, "$feature.NombreFalla", 11, bold=True, halo_pt=1.5)
    print(f"  OK Fallas por tipo cinemático ({len(labels_ok)}):")
    for line in labels_ok:
        print(f"    {line}")


def update_pliegues(lyr):
    """Solo Sinclinal de Venecia en leyenda; sin clase default [...] ."""
    cim = lyr.getDefinition("V3")
    renderer = arcpy.cim.CreateCIMObjectFromClassName("CIMUniqueValueRenderer", "V3")
    renderer.fields = ["NombrePliegue"]
    # Sin default => no aparece [...] en la leyenda
    renderer.useDefaultSymbol = False
    renderer.isDefaultSymbolVisible = False
    renderer.defaultLabel = ""
    renderer.defaultSymbol = build_line_symbol([solid_stroke(1.5, (0, 0, 0), None)])

    group = arcpy.cim.CreateCIMObjectFromClassName("CIMUniqueValueGroup", "V3")
    group.heading = "Ejes de pliegues"
    stroke = solid_stroke(2.5, (0, 0, 0), None)
    marker = character_marker_along_line(
        8746, size_pt=8.0, spacing_pt=20.0, offset=4.0, font_family="Segoe UI Symbol"
    )
    sym = build_line_symbol([marker, stroke])
    group.classes = [
        make_uv_class("Sinclinal de Venecia", "Sinclinal de Venecia", sym)
    ]
    renderer.groups = [group]
    cim.renderer = renderer
    lyr.setDefinition(cim)
    configure_labels(lyr, "$feature.NombrePliegue", 11, bold=True, halo_pt=1.5)
    print("  OK Pliegues: Sinclinal de Venecia (sin [...] en leyenda)")


def update_volcanes(lyr):
    """Etiquetas solo en mapa principal (no inset), NW exterior sin tapar polígono."""
    cim = lyr.getDefinition("V3")
    try:
        if hasattr(cim.renderer, "heading"):
            cim.renderer.heading = "Cuerpos Volcánicos"
        sym = cim.renderer.symbol.symbol
        for layer in sym.symbolLayers:
            if type(layer).__name__ == "CIMSolidFill":
                # Verde forestal ~65% opacidad
                layer.color = rgb(34, 139, 34, 65)
            elif type(layer).__name__ == "CIMSolidStroke":
                layer.color = rgb(0, 100, 0, 100)
                layer.width = 1.0
        lyr.setDefinition(cim)
    except Exception as ex:
        print(f"  Aviso simbología Volcanes: {ex}")

    configure_labels(lyr, "$feature.Name", 12, bold=True, halo_pt=1.5)

    cim2 = lyr.getDefinition("V3")
    for lc in cim2.labelClasses:
        lc.visibility = True
        lc.expression = "$feature.Name"
        # Visibles a 1:45k; ocultas en inset (~1:400k–550k)
        lc.minimumScale = 100000.0  # Out Beyond
        lc.maximumScale = 0.0

        mp = lc.maplexLabelPlacementProperties
        mp.featureType = "Polygon"
        mp.polygonFeatureType = "General"
        mp.polygonPlacementMethod = "HorizontalAroundPolygon"
        mp.canPlaceLabelOutsidePolygon = True
        mp.canPlaceLabelOnTopOfFeature = False
        mp.neverRemoveLabel = True
        mp.primaryOffset = 6.0
        mp.primaryOffsetUnit = "Point"
        mp.labelLargestPolygon = True
        mp.multiPartOption = "OneLabelPerPart"

        # Prioridad: izquierda superior (aboveLeft = 1)
        ez = mp.polygonExternalZones
        ez.aboveLeft = 1
        ez.aboveCenter = 2
        ez.centerLeft = 3
        ez.aboveRight = 4
        ez.centerRight = 5
        ez.belowLeft = 6
        ez.belowCenter = 7
        ez.belowRight = 8
        ez.center = 0

        iz = mp.polygonInternalZones
        iz.center = 0
        iz.aboveLeft = 0
        iz.aboveCenter = 0
        iz.aboveRight = 0
        iz.centerLeft = 0
        iz.centerRight = 0
        iz.belowLeft = 0
        iz.belowCenter = 0
        iz.belowRight = 0

        # Texto negro + halo blanco (no blanco sobre el polígono)
        ts = lc.textSymbol.symbol
        ts.height = 12.0
        ts.fontFamilyName = "Arial"
        ts.fontStyleName = "Bold"
        ts.haloSize = 1.5
        ts.haloSymbol = white_halo_symbol(1.5)
        for sl in getattr(ts, "symbolLayers", []) or []:
            if type(sl).__name__ == "CIMSolidFill":
                sl.color = rgb(0, 0, 0, 100)

    lyr.setDefinition(cim2)
    lyr.showLabels = True
    print(
        "  OK Volcanes: etiquetas NW exterior; ocultas en inset (Out Beyond 1:100k)"
    )


def update_hillshade(lyr):
    cim = lyr.getDefinition("V3")
    cim.transparency = 30.0
    try:
        cim.blendingMode = "Multiply"
    except Exception:
        pass
    lyr.setDefinition(cim)
    print("  OK Hillshade 30% / Multiply")


def order_toc(amap):
    names_top_to_bottom = [
        "Lineamientos_VF",
        "Fallas Locales",
        "Pliegues Locales",
        "Volcanes",
        "Hillshade_DEM_V_Fr.tif",
        "DEM_Suave_Venecia_Fr_ProjectRaster.tif",
        "DEM_Venecia_Fredonia_Final.tif",
    ]
    layers = {lyr.name: lyr for lyr in amap.listLayers()}
    for i, name in enumerate(names_top_to_bottom):
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
        prev = names_top_to_bottom[i - 1]
        if prev not in layers:
            continue
        try:
            amap.moveLayer(layers[prev], lyr, "AFTER")
        except Exception as ex:
            print(f"  Aviso moveLayer {name}: {ex}")
    # Ocultar capas auxiliares
    hide = {
        "Mapa_Geologico_de_Colombia_2015_Antioquia",
        "Red_Hidrografica_V1000",
        "Red_Drenaje_P1000.tif",
        "Flow_Accum.tif",
        "Flow_Dir.tif",
        "Fill_Dem_VF.tif",
        "Lineamientos_Curvature_Surface_Ven_Fred.tif",
    }
    for lyr in amap.listLayers():
        if lyr.name in hide:
            lyr.visible = False
    print("  OK Orden TOC (vectores sobre DEM)")


# Layout Carta (composición tipo ejemplo)
def configure_page_and_frames(lyt, amap):
    """
    Composición del ejemplo:
    - Mapa principal a la izquierda (escala 1:45.000)
    - Inset regional arriba-derecha (~1:400.000)
    - Leyenda abajo-derecha
    - Norte + barra de escala abajo/arriba izquierda
    """
    lyt.pageUnits = "INCH"
    try:
        lyt.changePageSize(PAGE_W, PAGE_H, resize_elements=False)
    except TypeError:
        lyt.pageWidth = PAGE_W
        lyt.pageHeight = PAGE_H

    map_w = PAGE_W - 2 * MARGIN - RIGHT_COL_W - 0.15
    map_h = PAGE_H - MARGIN - 0.80

    mf = lyt.listElements("MAPFRAME_ELEMENT", "Marco de mapa")[0]
    mf.elementPositionX = MARGIN
    mf.elementPositionY = 0.80
    mf.elementWidth = map_w
    mf.elementHeight = map_h
    mf.camera.scale = SCALE
    mf.camera.X = MAP_CENTER_X
    mf.camera.Y = MAP_CENTER_Y

    # Inset regional (fallas de contexto)
    insets = lyt.listElements("MAPFRAME_ELEMENT", "Marco de mapa 1")
    if insets:
        inset = insets[0]
        inset.elementWidth = RIGHT_COL_W
        inset.elementHeight = 3.10
        inset.elementPositionX = PAGE_W - MARGIN - RIGHT_COL_W
        inset.elementPositionY = PAGE_H - MARGIN - inset.elementHeight
        inset.camera.X = MAP_CENTER_X
        inset.camera.Y = MAP_CENTER_Y
        inset.camera.scale = INSET_SCALE
        # Etiquetas de fallas útiles en el inset
        try:
            fallas = find_layer(amap, "Fallas Locales")
            fallas.showLabels = True
        except Exception:
            pass

    # Norte (esquina superior izquierda del mapa)
    for na in lyt.listElements("MAPSURROUND_ELEMENT", "Flecha de norte"):
        na.elementWidth = 0.40
        na.elementHeight = 0.60
        na.elementPositionX = MARGIN + 0.12
        na.elementPositionY = PAGE_H - MARGIN - 0.85

    # Barra de escala
    for sb in lyt.listElements("MAPSURROUND_ELEMENT", "Barra de escala"):
        sb.elementWidth = 2.6
        sb.elementHeight = 0.32
        sb.elementPositionX = MARGIN + 0.08
        sb.elementPositionY = 0.28

    # Texto de escala (rojo, como en el ejemplo)
    for te in lyt.listElements("TEXT_ELEMENT", "Texto"):
        te.text = SCALE_TEXT
        te.elementPositionX = MARGIN + 2.85
        te.elementPositionY = 0.32
        try:
            te_cim = te.getDefinition("V3")
            g = te_cim.graphic
            sym = g.symbol.symbol
            sym.height = 11
            sym.fontFamilyName = "Arial"
            sym.fontStyleName = "Bold"
            for sl in getattr(sym, "symbolLayers", []) or []:
                if type(sl).__name__ == "CIMSolidFill":
                    sl.color = rgb(200, 0, 0, 100)
            te.setDefinition(te_cim)
        except Exception:
            pass

    print("  OK Página Letter 11x8.5, mapa 1:60.000, inset 1:400.000")
    return mf


def configure_graticule(aprx, mf):
    aprx.updateStyles(
        ["ArcGIS 2D", "ArcGIS 3D", "ArcGIS Colors", "ColorBrewer Schemes (RGB)"]
    )
    try:
        mf.removeGrids("*")
    except Exception:
        pass

    style_items = aprx.listStyleItems(
        "ArcGIS 2D", "GRID", "Black Vertical Label Graticule"
    )
    if not style_items:
        style_items = aprx.listStyleItems("ArcGIS 2D", "GRID", "*Graticule*")
    if not style_items:
        print("  AVISO: sin estilo de graticule")
        return

    mf.addGrid(style_items[0])
    interval_deg = 2.5 / 60.0  # 2'30"
    dms_template = (
        '<dyn type="grid" units="dms" decimalPlaces="0" '
        'showDirections="True" showZeroMinutes="False" '
        'showZeroSeconds="False" zeroPad="True"/>'
    )
    mf_cim = mf.getDefinition("V3")
    for grid in mf_cim.grids or []:
        if "Graticule" not in type(grid).__name__:
            continue
        grid.isAutoScaled = False
        grid.name = "Graticule DMS"
        for gl in grid.gridLines or []:
            pat = getattr(gl, "pattern", None)
            if pat is not None and getattr(pat, "start", 0) in (0, None):
                newpat = arcpy.cim.CreateCIMObjectFromClassName("CIMGridPattern", "V3")
                newpat.interval = interval_deg
                newpat.start = 0
                newpat.stop = getattr(pat, "stop", 1) or 1
                newpat.gap = getattr(pat, "gap", 0) or 0
                gl.pattern = newpat
            for tick_attr in ("fromTick", "toTick"):
                tick = getattr(gl, tick_attr, None)
                if tick is None:
                    continue
                endpoint = getattr(tick, "gridEndpoint", None)
                if endpoint is None:
                    continue
                tmpl = getattr(endpoint, "gridLabelTemplate", None)
                if tmpl is not None and hasattr(tmpl, "dynamicStringTemplate"):
                    tmpl.dynamicStringTemplate = dms_template
    mf.setDefinition(mf_cim)
    print("  OK Graticule DMS cada 2'30\" (etiquetas verticales laterales)")


def _set_text_symbol(te, size_pt, bold=True, color_rgb=(0, 0, 0)):
    try:
        te_cim = te.getDefinition("V3")
        sym = te_cim.graphic.symbol.symbol
        sym.height = float(size_pt)
        sym.fontFamilyName = "Arial"
        sym.fontStyleName = "Bold" if bold else "Regular"
        for sl in getattr(sym, "symbolLayers", []) or []:
            if type(sl).__name__ == "CIMSolidFill":
                sl.color = rgb(*color_rgb)
        te.setDefinition(te_cim)
    except Exception as ex:
        print(f"  Aviso texto CIM ({te.name}): {ex}")


def configure_title(aprx, lyt):
    """Título del mapa + escala 1:60.000 con fondo blanco."""
    title_name = "Titulo_mapa"
    bg_name = "Titulo_fondo"
    title_text = (
        "Mapa de estructuras del campo volcánico Venecia-Fredonia\r\n"
        + SCALE_TEXT
    )
    map_w = PAGE_W - 2 * MARGIN - RIGHT_COL_W - 0.15
    x0 = MARGIN
    y0 = PAGE_H - 0.55
    x1 = MARGIN + map_w
    y1 = PAGE_H - 0.08

    corners = [
        arcpy.Point(x0, y0),
        arcpy.Point(x1, y0),
        arcpy.Point(x1, y1),
        arcpy.Point(x0, y1),
        arcpy.Point(x0, y0),
    ]
    poly = arcpy.Polygon(arcpy.Array(corners))

    # Rectángulo blanco detrás del título
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
    try:
        bg_cim = bg.getDefinition("V3")
        fill = arcpy.cim.CreateCIMObjectFromClassName("CIMSolidFill", "V3")
        fill.color = rgb(255, 255, 255, 100)
        stroke = arcpy.cim.CreateCIMObjectFromClassName("CIMSolidStroke", "V3")
        stroke.color = rgb(90, 90, 90, 100)
        stroke.width = 0.5
        poly_sym = arcpy.cim.CreateCIMObjectFromClassName("CIMPolygonSymbol", "V3")
        poly_sym.symbolLayers = [stroke, fill]
        # Asignar símbolo al graphic
        g = bg_cim.graphic
        if hasattr(g, "symbol"):
            ref = arcpy.cim.CreateCIMObjectFromClassName("CIMSymbolReference", "V3")
            ref.symbol = poly_sym
            g.symbol = ref
        bg.setDefinition(bg_cim)
    except Exception as ex:
        print(f"  Aviso símbolo fondo título: {ex}")

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
            title_text,
            text_size=14,
            font_family_name="Arial",
            font_style_name="Bold",
            name=title_name,
        )
    else:
        existing.text = title_text

    existing.elementPositionX = x0
    existing.elementPositionY = y0
    existing.elementWidth = x1 - x0
    existing.elementHeight = y1 - y0
    existing.visible = True
    _set_text_symbol(existing, 14, bold=True, color_rgb=(0, 0, 0))

    print("  OK Título con fondo blanco + escala 1:60.000")
    return existing


def configure_citation(aprx, lyt):
    """Oculta cita suelta del layout: la referencia APA queda solo en la leyenda."""
    for te in lyt.listElements("TEXT_ELEMENT"):
        if te.name == "Cita_Lopez_2006":
            te.visible = False
            print("  OK Cita APA solo en leyenda (texto suelto oculto)")
            return te
    print("  OK Sin texto de cita suelto")
    return None


def _set_cim_text_size(sym_ref, size_pt, bold=False):
    """Ajusta altura de un CIMSymbolReference de texto (título/etiquetas leyenda)."""
    if sym_ref is None or getattr(sym_ref, "symbol", None) is None:
        return
    sym = sym_ref.symbol
    try:
        sym.height = float(size_pt)
        sym.fontFamilyName = "Arial"
        sym.fontStyleName = "Bold" if bold else "Regular"
    except Exception:
        pass


def configure_scale_elements(lyt):
    """Barra y texto de escala más pequeños, fuera de la caja de leyenda."""
    sb_x = PAGE_W - MARGIN - RIGHT_COL_W
    sb_y = 0.22
    for sb in lyt.listElements("MAPSURROUND_ELEMENT", "Barra de escala"):
        sb.visible = True
        sb.elementPositionX = sb_x
        sb.elementPositionY = sb_y
        try:
            cim = sb.getDefinition("V3")
            # Tamaño real de la barra (elementWidth se deriva de esto)
            cim.division = 1.0
            cim.divisions = 2
            cim.subdivisions = 1
            cim.barHeight = 6.0
            if hasattr(cim, "divisionMarkHeight"):
                cim.divisionMarkHeight = 6
            if hasattr(cim, "subdivisionMarkHeight"):
                cim.subdivisionMarkHeight = 4
            for attr in ("labelSymbol", "unitLabelSymbol", "numberSymbol"):
                ref = getattr(cim, attr, None)
                if ref is not None and getattr(ref, "symbol", None) is not None:
                    ref.symbol.height = 7
                    ref.symbol.fontFamilyName = "Arial"
            sb.setDefinition(cim)
        except Exception as ex:
            print(f"  Aviso CIM barra escala: {ex}")
            sb.elementWidth = 2.35
            sb.elementHeight = 0.28

    for te in lyt.listElements("TEXT_ELEMENT", "Texto"):
        te.text = SCALE_TEXT
        te.visible = True
        te.elementPositionX = sb_x
        te.elementPositionY = 0.05
        te.elementWidth = 2.35
        te.elementHeight = 0.18
        try:
            te_cim = te.getDefinition("V3")
            sym = te_cim.graphic.symbol.symbol
            sym.height = 8.0
            sym.fontFamilyName = "Arial"
            sym.fontStyleName = "Bold"
            for sl in getattr(sym, "symbolLayers", []) or []:
                if type(sl).__name__ == "CIMSolidFill":
                    sl.color = rgb(0, 0, 0, 100)
            te.setDefinition(te_cim)
        except Exception as ex:
            print(f"  Aviso texto escala: {ex}")
    print("  OK Escala reducida:", SCALE_TEXT)


def configure_legend(lyt, mf, amap):
    """Leyenda abajo-derecha, tipografía legible, sin residuos [...]."""
    x0 = PAGE_W - MARGIN - RIGHT_COL_W
    # Dejar espacio abajo para la barra de escala reducida
    y0 = MARGIN + 0.55
    y1 = PAGE_H - MARGIN - 3.10 - 0.12

    legend = None
    for leg in lyt.listElements("LEGEND_ELEMENT"):
        if leg.name == "Leyenda" and legend is None:
            legend = leg
            legend.visible = True
        else:
            leg.visible = False
            if not str(leg.name).startswith("Leyenda_old"):
                leg.name = f"Leyenda_old_{leg.name}"

    if legend is None:
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

    legend.elementPositionX = x0
    legend.elementPositionY = y0
    legend.elementWidth = RIGHT_COL_W
    legend.elementHeight = max(2.5, y1 - y0)

    legend.syncNewLayer = False
    legend.syncLayerVisibility = False
    legend.syncLayerOrder = False
    legend.showTitle = True
    legend.title = "Leyenda"
    try:
        legend.fittingStrategy = "AdjustColumnsAndSize"
        legend.columnCount = 1
    except Exception:
        pass
    # Sin descripciones separadas (evita artefactos tipo "L. tip..." / parches extra)
    try:
        legend.showTitle = True
        for it in legend.items:
            if hasattr(it, "showDescriptions"):
                it.showDescriptions = False
            if hasattr(it, "showDescription"):
                it.showDescription = False
            if hasattr(it, "showHeading"):
                it.showHeading = True
    except Exception:
        pass

    keep = {
        "Lineamientos_VF",
        "Fallas Locales",
        "Pliegues Locales",
        "Volcanes",
    }
    # Asegurar que existan los ítems deseados
    existing = {it.name for it in legend.items}
    for name in keep:
        if name not in existing:
            try:
                legend.addItem(find_layer(amap, name))
            except Exception as ex:
                print(f"  Aviso addItem {name}: {ex}")

    for item in list(legend.items):
        if item.name not in keep:
            try:
                legend.removeItem(item)
            except Exception as ex:
                print(f"  Aviso removeItem {item.name}: {ex}")

    order = ["Lineamientos_VF", "Fallas Locales", "Pliegues Locales", "Volcanes"]
    items_by_name = {it.name: it for it in legend.items}
    for i, name in enumerate(order):
        if i == 0 or name not in items_by_name:
            continue
        prev = order[i - 1]
        if prev in items_by_name:
            try:
                legend.moveItem(items_by_name[prev], items_by_name[name], "AFTER")
            except Exception:
                pass

    # Renombrar ítems de leyenda (grupos lógicos)
    rename = {
        "Lineamientos_VF": "Lineamientos Geológicos",
        "Fallas Locales": "Fallas Tectónicas Regionales",
        "Pliegues Locales": "Ejes de Pliegues (Sinclinal de Venecia)",
        "Volcanes": "Cuerpos Volcánicos",
    }
    try:
        for it in legend.items:
            if it.name in rename:
                # name del LegendItem suele ser el de la capa; heading vía CIM
                pass
        leg_cim = legend.getDefinition("V3")
        # Tipografía más grande y legible
        _set_cim_text_size(getattr(leg_cim, "titleSymbol", None), 13, bold=True)
        for item in getattr(leg_cim, "items", []) or []:
            if hasattr(item, "showHeading"):
                item.showHeading = True
            if hasattr(item, "showLayerName"):
                item.showLayerName = False
            if hasattr(item, "showDescription"):
                item.showDescription = False
            if hasattr(item, "showDescriptions"):
                item.showDescriptions = False
            if hasattr(item, "showLabels"):
                item.showLabels = True
            try:
                item.arrangement = "PatchLabel"
            except Exception:
                pass
            _set_cim_text_size(getattr(item, "labelSymbol", None), 11, bold=False)
            _set_cim_text_size(getattr(item, "headingSymbol", None), 11, bold=True)
            _set_cim_text_size(getattr(item, "descriptionSymbol", None), 8, bold=False)
            try:
                item.patchWidth = 32
                item.patchHeight = 14
            except Exception:
                pass
        # Fondo 85%
        fill = arcpy.cim.CreateCIMObjectFromClassName("CIMSolidFill", "V3")
        fill.color = rgb(255, 255, 255, 85)
        stroke = arcpy.cim.CreateCIMObjectFromClassName("CIMSolidStroke", "V3")
        stroke.color = rgb(80, 80, 80, 100)
        stroke.width = 0.6
        bg_poly = arcpy.cim.CreateCIMObjectFromClassName("CIMPolygonSymbol", "V3")
        bg_poly.symbolLayers = [stroke, fill]
        bg_ref = arcpy.cim.CreateCIMObjectFromClassName("CIMSymbolReference", "V3")
        bg_ref.symbol = bg_poly
        border_poly = arcpy.cim.CreateCIMObjectFromClassName("CIMPolygonSymbol", "V3")
        border_poly.symbolLayers = [stroke]
        border_ref = arcpy.cim.CreateCIMObjectFromClassName("CIMSymbolReference", "V3")
        border_ref.symbol = border_poly
        if leg_cim.graphicFrame:
            leg_cim.graphicFrame.backgroundSymbol = bg_ref
            leg_cim.graphicFrame.borderSymbol = border_ref
            leg_cim.graphicFrame.backgroundGapX = 5
            leg_cim.graphicFrame.backgroundGapY = 5
        leg_cim.defaultPatchWidth = 32
        leg_cim.defaultPatchHeight = 14
        try:
            leg_cim.minFontSize = 9
        except Exception:
            pass
        legend.setDefinition(leg_cim)
    except Exception as ex:
        print(f"  Aviso leyenda CIM: {ex}")

    for name in keep:
        try:
            find_layer(amap, name).visible = True
        except Exception:
            pass

    print(f"  OK Leyenda: {[i.name for i in legend.items]}")
    return legend


def export_pdf(lyt):
    os.makedirs(os.path.dirname(PDF_PATH), exist_ok=True)
    if os.path.exists(PDF_PATH):
        try:
            os.remove(PDF_PATH)
        except OSError:
            pass
    try:
        lyt.exportToPDF(
            PDF_PATH,
            resolution=300,
            image_quality="BEST",
            compress_vector_graphics=True,
            embed_fonts=True,
            output_as_image=False,
        )
    except TypeError:
        lyt.exportToPDF(PDF_PATH, resolution=300)
    print(f"  OK PDF vectorial 300 DPI: {PDF_PATH}")


# Main
def main():
    print("=" * 60)
    print("Diseño1 — Escala 1:60.000, título fondo blanco, leyenda limpia")
    print("=" * 60)

    if not os.path.exists(APRX_PATH):
        raise FileNotFoundError(APRX_PATH)

    aprx = arcpy.mp.ArcGISProject(APRX_PATH)
    amap = aprx.listMaps("Map")[0]
    lyt = find_layout(aprx, "1")
    print(f"Layout: {lyt.name!r}")

    print("\n[1] Simbología limpia")
    update_lineamientos(find_layer(amap, "Lineamientos_VF"))
    update_fallas(find_layer(amap, "Fallas Locales"))
    update_pliegues(find_layer(amap, "Pliegues Locales"))
    update_volcanes(find_layer(amap, "Volcanes"))

    print("\n[2] Escala del marco 1:60.000")
    mfs = lyt.listElements("MAPFRAME_ELEMENT", "Marco de mapa")
    mf = mfs[0] if mfs else None
    if mf:
        mf.camera.scale = SCALE
    for te in lyt.listElements("TEXT_ELEMENT", "Texto"):
        te.text = SCALE_TEXT

    print("\n[3] Título (fondo blanco) y cita")
    configure_title(aprx, lyt)
    configure_citation(aprx, lyt)

    print("\n[4] Leyenda compacta + tipografía")
    if mf:
        configure_legend(lyt, mf, amap)

    print("\n[5] Escala reducida (fuera de la leyenda)")
    configure_scale_elements(lyt)

    print("\n[6] Guardar proyecto")
    aprx.save()
    print(f"  OK {APRX_PATH}")

    print("\n[7] Exportar PDF")
    export_pdf(lyt)

    print("\nListo.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        sys.exit(1)
