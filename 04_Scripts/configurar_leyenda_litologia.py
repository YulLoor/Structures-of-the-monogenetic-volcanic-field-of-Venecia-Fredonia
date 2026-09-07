# -*- coding: utf-8 -*-
"""
Leyenda de litologia para Diseno1 y Diseno2:

1. Formacion Combia (andesitas y basalto)
2. Formacion Amaga (arenitas, arcillolitas y carbones)
3. Porfidos andesiticos y daciticos
4. Muestras CVMVF

No cambia la escala ni el inset. Ejecutar:
  "C:\\Program Files\\ArcGIS\\Pro\\bin\\Python\\envs\\arcgispro-py3\\python.exe" ^
    04_Scripts\\configurar_leyenda_litologia.py
"""

from __future__ import annotations

import os
import sys
import traceback

import arcpy

ROOT = r"C:\PROYECTO_GIS_VF_Antigraviti"
APRX_PATH = os.path.join(ROOT, "Venecia_Fredonia_Analisis_Estructural.aprx")

CLIP_NAME = "Unidades_Cronoestratigraficas_clip"
LITO_NAME = "Litología"
MUESTRAS_NAME = "Muestras CVMVF"
RHR_NAME = "Rumbo y buzamiento"
VOLC_NAME = "Volcanes"
LINEAM_NAME = "Lineamientos_VF"
FALLAS_NAME = "Fallas Locales"
PLIEGUES_NAME = "Pliegues Locales"

STRUCTURAL_LEGEND = [LINEAM_NAME, FALLAS_NAME, PLIEGUES_NAME, VOLC_NAME]

# Orden pedido para la leyenda unica de Diseno1
LEGEND_ORDER = [
    MUESTRAS_NAME,
    RHR_NAME,
    LINEAM_NAME,
    FALLAS_NAME,
    PLIEGUES_NAME,
    VOLC_NAME,
    LITO_NAME,
]

MUESTRAS_SIZE_PT = 11.0
MUESTRAS_LABEL_PT = 10.0

MAIN_MF_NAME = "Marco de mapa"
INSET_MF_NAME = "Marco de mapa 1"

# Capas de simbolo unico: parche y texto en la misma fila
ONE_ROW_ITEMS = {MUESTRAS_NAME, RHR_NAME}

# Volcanes usa un renderer simple sin encabezado propio: el nombre de capa
# hace de encabezado para que no se lea como parte del grupo de pliegues
LAYER_NAME_ITEMS = {VOLC_NAME}
VOLC_LEGEND_LABEL = "Cuerpos volcánicos"

PAGE_W = 11.0
PAGE_H = 8.5
MARGIN = 0.30
RIGHT_COL_W = 2.70

# AUCR_CODG del Atlas SGC en el recorte VF
LITO_CLASSES = [
    (
        "10339",
        "Formación Combia (andesitas y basalto)",
    ),
    (
        "10250",
        "Formación Amagá (arenitas, arcillolitas y carbones)",
    ),
    (
        "10274",
        "Pórfidos andesíticos y dacíticos",
    ),
]
LITO_CODES = [c[0] for c in LITO_CLASSES]
LITO_QUERY = "AUCR_CODG IN (10339, 10250, 10274)"


def rgb(r, g, b, a=100):
    c = arcpy.cim.CreateCIMObjectFromClassName("CIMRGBColor", "V3")
    c.values = [float(r), float(g), float(b), float(a)]
    return c


def find_layer(amap, name):
    for lyr in amap.listLayers():
        if lyr.name == name:
            return lyr
    low = name.lower()
    for lyr in amap.listLayers():
        if low in (lyr.name or "").lower():
            return lyr
    return None


def find_layout(aprx, ends_with):
    for lyt in aprx.listLayouts():
        if abs(lyt.pageWidth - 11.0) < 0.3 and abs(lyt.pageHeight - 8.5) < 0.3:
            if lyt.name.endswith(ends_with) and (
                ends_with != "1" or not lyt.name.endswith("2")
            ):
                return lyt
    return None


def class_code(cl):
    try:
        return str(cl.values[0].fieldValues[0])
    except Exception:
        return ""


def collect_lito_classes(src_lyr):
    """Copia las 3 clases del Atlas (simbolo + codigo) con etiquetas nuevas."""
    cim = src_lyr.getDefinition("V3")
    rend = cim.renderer
    by_code = {}
    for g in rend.groups or []:
        for cl in g.classes or []:
            by_code[class_code(cl)] = cl
    out = []
    missing = []
    for code, label in LITO_CLASSES:
        cl = by_code.get(code)
        if cl is None:
            missing.append(code)
            continue
        cl.label = label
        cl.description = label
        cl.visible = True
        out.append(cl)
    if missing:
        print(f"  Aviso clases no halladas: {missing}")
    return out, cim, rend


def relabel_clip_groups(clip_lyr):
    """En el clip completo: grupo Litologia (3) + resto, para el TOC."""
    keep_cls, cim, rend = collect_lito_classes(clip_lyr)
    if not keep_cls:
        return
    other = []
    keep_codes = set(LITO_CODES)
    for g in rend.groups or []:
        for cl in g.classes or []:
            if class_code(cl) not in keep_codes:
                other.append(cl)
    g1 = arcpy.cim.CreateCIMObjectFromClassName("CIMUniqueValueGroup", "V3")
    g1.heading = "Litología"
    g1.classes = keep_cls
    g2 = arcpy.cim.CreateCIMObjectFromClassName("CIMUniqueValueGroup", "V3")
    g2.heading = ""
    g2.classes = other
    rend.groups = [g1, g2] if other else [g1]
    clip_lyr.setDefinition(cim)
    print(f"  OK Etiquetas litologia en {clip_lyr.name}")


def apply_three_class_renderer(lito_lyr, keep_cls):
    cim = lito_lyr.getDefinition("V3")
    rend = arcpy.cim.CreateCIMObjectFromClassName("CIMUniqueValueRenderer", "V3")
    rend.fields = ["AUCR_CODG"]
    rend.defaultLabel = ""
    rend.useDefaultSymbol = False
    rend.isDefaultSymbolVisible = False
    g1 = arcpy.cim.CreateCIMObjectFromClassName("CIMUniqueValueGroup", "V3")
    g1.heading = "Litología"
    g1.classes = keep_cls
    rend.groups = [g1]
    cim.renderer = rend
    lito_lyr.setDefinition(cim)


def add_or_update_lito_layer(amap, clip_lyr):
    keep_cls, _cim, _rend = collect_lito_classes(clip_lyr)
    if not keep_cls:
        raise RuntimeError("No se encontraron las clases Combia / Amaga / porfidos")

    src = None
    try:
        src = clip_lyr.dataSource
    except Exception:
        src = None
    if not src or not arcpy.Exists(src):
        raise RuntimeError("No hay fuente de Unidades_Cronoestratigraficas_clip")

    for lyr in list(amap.listLayers()):
        if lyr.name == LITO_NAME:
            try:
                amap.removeLayer(lyr)
            except Exception:
                pass

    lito = amap.addDataFromPath(src)
    try:
        lito.name = LITO_NAME
    except Exception:
        pass
    try:
        lito.definitionQuery = LITO_QUERY
    except Exception as ex:
        print(f"  Aviso definitionQuery: {ex}")

    apply_three_class_renderer(lito, keep_cls)
    lito.visible = True

    try:
        amap.moveLayer(clip_lyr, lito, "BEFORE")
    except Exception:
        pass
    print(f"  OK Capa {LITO_NAME} ({amap.name})")
    return lito


def red_circle_symbol_ref(size_pt=14.0):
    """Circulo rojo vectorial (CIMVectorMarker): se dibuja de forma fiable."""
    import math

    fill = arcpy.cim.CreateCIMObjectFromClassName("CIMSolidFill", "V3")
    fill.color = rgb(255, 0, 0, 100)
    stroke = arcpy.cim.CreateCIMObjectFromClassName("CIMSolidStroke", "V3")
    stroke.color = rgb(80, 0, 0, 100)
    stroke.width = 1.5
    stroke.enable = True
    poly_sym = arcpy.cim.CreateCIMObjectFromClassName("CIMPolygonSymbol", "V3")
    poly_sym.symbolLayers = [stroke, fill]

    pts = [
        arcpy.Point(math.cos(2 * math.pi * i / 32.0), math.sin(2 * math.pi * i / 32.0))
        for i in range(33)
    ]
    graphic = arcpy.cim.CreateCIMObjectFromClassName("CIMMarkerGraphic", "V3")
    # Debe ser el simbolo directo: un CIMSymbolReference aqui se serializa como null
    graphic.symbol = poly_sym
    graphic.geometry = arcpy.Polygon(arcpy.Array(pts))

    vm = arcpy.cim.CreateCIMObjectFromClassName("CIMVectorMarker", "V3")
    vm.size = float(size_pt)
    vm.enable = True
    vm.frame = arcpy.Extent(-1, -1, 1, 1)
    vm.markerGraphics = [graphic]

    pt_sym = arcpy.cim.CreateCIMObjectFromClassName("CIMPointSymbol", "V3")
    pt_sym.symbolLayers = [vm]
    ref = arcpy.cim.CreateCIMObjectFromClassName("CIMSymbolReference", "V3")
    ref.symbol = pt_sym
    return ref


def style_muestras_legend_label(lyr):
    """Punto rojo visible + etiqueta de leyenda en la misma fila que el parche."""
    cim = lyr.getDefinition("V3")
    rend = arcpy.cim.CreateCIMObjectFromClassName("CIMSimpleRenderer", "V3")
    rend.symbol = red_circle_symbol_ref(MUESTRAS_SIZE_PT)
    rend.label = MUESTRAS_NAME
    rend.description = MUESTRAS_NAME
    cim.renderer = rend
    cim.minScale = 0
    cim.maxScale = 0
    lyr.setDefinition(cim)
    lyr.visible = True
    print(f"  OK Punto rojo {MUESTRAS_SIZE_PT:.0f} pt + etiqueta de leyenda")


def configure_muestras_labels(lyr):
    """Etiquetas RV-* con [Codigo], negro sobre halo blanco, sin limite de escala."""
    cim = lyr.getDefinition("V3")
    if not cim.labelClasses:
        print("  Aviso: Muestras sin clase de etiqueta")
        return
    lc = cim.labelClasses[0]
    lc.visibility = True
    lc.expressionEngine = "Python"
    lc.expression = "[Codigo]"
    lc.minimumScale = 0.0
    lc.maximumScale = 0.0
    try:
        lc.minScale = 0
        lc.maxScale = 0
    except Exception:
        pass

    # Desplazar la etiqueta del punto: si va centrada, el halo tapa el circulo
    try:
        mp = lc.maplexLabelPlacementProperties
        mp.featureType = "Point"
        mp.pointPlacementMethod = "AroundPoint"
        mp.primaryOffset = 4.0
        mp.primaryOffsetUnit = "Point"
        mp.canPlaceLabelOutsidePolygon = True
        mp.thinDuplicateLabels = False
    except Exception as ex:
        print(f"  Aviso posicion etiquetas: {ex}")
    try:
        sp = lc.standardLabelPlacementProperties
        sp.featureType = "Point"
        sp.pointPlacementMethod = "AroundPoint"
    except Exception:
        pass

    ts = lc.textSymbol.symbol
    ts.height = MUESTRAS_LABEL_PT
    ts.fontFamilyName = "Arial"
    ts.fontStyleName = "Bold"
    for sl in getattr(ts, "symbolLayers", []) or []:
        if type(sl).__name__ == "CIMSolidFill":
            sl.color = rgb(0, 0, 0, 100)
    halo_fill = arcpy.cim.CreateCIMObjectFromClassName("CIMSolidFill", "V3")
    halo_fill.color = rgb(255, 255, 255, 100)
    halo = arcpy.cim.CreateCIMObjectFromClassName("CIMPolygonSymbol", "V3")
    halo.symbolLayers = [halo_fill]
    try:
        ts.haloSize = 1.5
        ts.haloSymbol = halo
    except Exception:
        pass

    lyr.setDefinition(cim)
    lyr.showLabels = True
    print(f"  OK Etiquetas [Codigo] {MUESTRAS_LABEL_PT:.0f} pt")


def _set_cim_text_size(sym_ref, size_pt, bold=False):
    if sym_ref is None or getattr(sym_ref, "symbol", None) is None:
        return
    sym = sym_ref.symbol
    try:
        sym.height = float(size_pt)
        sym.fontFamilyName = "Arial"
        sym.fontStyleName = "Bold" if bold else "Regular"
    except Exception:
        pass


def style_legend_frame(legend, order, x, y, w, h, title="Leyenda"):
    try:
        legend.syncNewLayer = False
        legend.syncLayerVisibility = False
        legend.syncLayerOrder = False
    except Exception:
        pass
    legend.showTitle = bool(title)
    legend.title = title or ""
    legend.elementPositionX = x
    legend.elementPositionY = y
    legend.elementWidth = w
    legend.elementHeight = h
    try:
        legend.fittingStrategy = "AdjustFontSize"
        legend.columnCount = 1
    except Exception:
        pass

    keep = set(order)

    existing = {it.name for it in legend.items}
    amap = None
    try:
        amap = legend.mapFrame.map
    except Exception:
        amap = None
    for name in order:
        if name not in existing and amap is not None:
            lyr = find_layer(amap, name)
            if lyr is not None:
                try:
                    legend.addItem(lyr)
                except Exception as ex:
                    print(f"  Aviso addItem {name}: {ex}")

    for item in list(legend.items):
        if item.name not in keep:
            try:
                legend.removeItem(item)
            except Exception as ex:
                print(f"  Aviso removeItem {item.name}: {ex}")

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

    def _apply_item_flags(item, n):
        # Capas de un solo simbolo: parche y texto en la misma fila, sin encabezado
        one_row = n in ONE_ROW_ITEMS
        try:
            item.isVisible = True
            item.autoVisibility = False
        except Exception:
            pass
        try:
            item.visible = True
        except Exception:
            pass
        if hasattr(item, "showHeading"):
            item.showHeading = not one_row
        if hasattr(item, "showLayerName"):
            item.showLayerName = n in LAYER_NAME_ITEMS
        if hasattr(item, "showLabels"):
            item.showLabels = True
        if hasattr(item, "showDescription"):
            item.showDescription = False
        if hasattr(item, "showDescriptions"):
            item.showDescriptions = False
        try:
            item.arrangement = "PatchLabel"
        except Exception:
            pass
        try:
            item.newColumn = False
        except Exception:
            pass
        try:
            if n == MUESTRAS_NAME:
                item.patchWidth = 16
                item.patchHeight = 12
            elif n == RHR_NAME:
                item.patchWidth = 22
                item.patchHeight = 16
            else:
                item.patchWidth = 22
                item.patchHeight = 8
        except Exception:
            pass

    try:
        for it in legend.items:
            _apply_item_flags(it, it.name)
    except Exception:
        pass

    try:
        leg_cim = legend.getDefinition("V3")
        _set_cim_text_size(getattr(leg_cim, "titleSymbol", None), 12, bold=True)
        try:
            leg_cim.columns = 1
            leg_cim.fittingStrategy = "AdjustFontSize"
            try:
                leg_cim.balanceColumns = False
            except Exception:
                pass
            try:
                leg_cim.makeColumnsSameWidth = False
            except Exception:
                pass
            leg_cim.minFontSize = 6
            leg_cim.itemGap = 2
            if hasattr(leg_cim, "horizontalItemGap"):
                leg_cim.horizontalItemGap = 8
            if hasattr(leg_cim, "classGap"):
                leg_cim.classGap = 0
            if hasattr(leg_cim, "headingGap"):
                leg_cim.headingGap = 1
            if hasattr(leg_cim, "itemGap"):
                leg_cim.itemGap = 1
            if hasattr(leg_cim, "groupGap"):
                leg_cim.groupGap = 2
        except Exception:
            pass
        for item in getattr(leg_cim, "items", []) or []:
            n = getattr(item, "name", "")
            _apply_item_flags(item, n)
            _set_cim_text_size(getattr(item, "labelSymbol", None), 7, bold=False)
            _set_cim_text_size(getattr(item, "headingSymbol", None), 9, bold=True)
            # Volcanes usa el nombre de capa como encabezado: mismo estilo
            _set_cim_text_size(getattr(item, "layerNameSymbol", None), 9, bold=True)
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
            leg_cim.graphicFrame.backgroundGapX = 4
            leg_cim.graphicFrame.backgroundGapY = 4
        legend.setDefinition(leg_cim)
        for it in legend.items:
            try:
                it.visible = True
            except Exception:
                pass
        c2 = legend.getDefinition("V3")
        try:
            c2.columns = 1
            c2.fittingStrategy = "AdjustFontSize"
        except Exception:
            pass
        for item in getattr(c2, "items", []) or []:
            _apply_item_flags(item, getattr(item, "name", ""))
        legend.setDefinition(c2)
    except Exception as ex:
        print(f"  Aviso leyenda CIM: {ex}")

    print(f"  OK Leyenda {legend.name}: {[i.name for i in legend.items]}")
    # Fijar marco (Adjust* a veces cambia la caja)
    legend.elementPositionX = x
    legend.elementPositionY = y
    legend.elementWidth = w
    legend.elementHeight = h


def _single_legend(lyt, mf):
    """Deja un unico elemento de leyenda llamado 'Leyenda' y oculta el resto."""
    legends = lyt.listElements("LEGEND_ELEMENT")
    legend = None
    for leg in legends:
        if leg.name == "Leyenda":
            legend = leg
            break
    if legend is None and legends:
        legend = legends[0]
        legend.name = "Leyenda"
    if legend is None:
        x0, y0, w, h = 7.45, 1.10, 3.20, 3.15
        corners = [
            arcpy.Point(x0, y0),
            arcpy.Point(x0 + w, y0),
            arcpy.Point(x0 + w, y0 + h),
            arcpy.Point(x0, y0 + h),
            arcpy.Point(x0, y0),
        ]
        legend = lyt.createMapSurroundElement(
            arcpy.Polygon(arcpy.Array(corners)), "LEGEND", mf, name="Leyenda"
        )
    legend.visible = True
    for leg in lyt.listElements("LEGEND_ELEMENT"):
        if leg is not legend and leg.name != "Leyenda":
            leg.visible = False
    return legend


def _inset_box(lyt):
    """Geometria del recuadro de ubicacion, para alinear y no encimar la leyenda."""
    for e in lyt.listElements("MAPFRAME_ELEMENT"):
        if e.name == INSET_MF_NAME:
            return (
                float(e.elementPositionX),
                float(e.elementPositionY),
                float(e.elementWidth),
            )
    return (PAGE_W - MARGIN - RIGHT_COL_W, 4.42, RIGHT_COL_W)


def update_layout_legend(lyt, include_structural):
    mf = None
    for e in lyt.listElements("MAPFRAME_ELEMENT"):
        if e.name == MAIN_MF_NAME:
            mf = e
            break
    if mf is None:
        mfs = lyt.listElements("MAPFRAME_ELEMENT")
        mf = mfs[0] if mfs else None
    if mf is None:
        raise RuntimeError("No hay marco de mapa en el layout")

    legend = _single_legend(lyt, mf)

    # El elemento se ancla en TopLeftCorner: 'y' es el borde superior
    bottom = MARGIN + 0.80
    if include_structural:
        ix, iy, iw = _inset_box(lyt)
        x, w = ix, iw
        y = iy - 0.16
        h = max(2.6, y - bottom)
        order = list(LEGEND_ORDER)
    else:
        x = PAGE_W - MARGIN - RIGHT_COL_W
        w = RIGHT_COL_W
        y = PAGE_H - MARGIN - 3.30
        h = max(2.6, y - bottom)
        order = [LITO_NAME, MUESTRAS_NAME]

    style_legend_frame(legend, order, x=x, y=y, w=w, h=h, title="Leyenda")

    # Barra y texto de escala bajo la leyenda; ambos se anclan por arriba,
    # asi que 'y' es el borde superior y hay que dejar sitio hacia abajo
    for sb in lyt.listElements("MAPSURROUND_ELEMENT"):
        n = (sb.name or "").lower()
        if "escala" in n or "scale" in n or "barra" in n:
            try:
                sb.elementPositionX = x
                sb.elementPositionY = 0.82
            except Exception:
                pass
    for te in lyt.listElements("TEXT_ELEMENT"):
        if te.visible and te.text and "Escala" in str(te.text):
            te.elementPositionX = x + w / 2.0
            te.elementPositionY = 0.44
    return legend


def configure_map(amap, show_structural=False):
    clip = find_layer(amap, CLIP_NAME)
    if clip is None:
        print(f"  Aviso: no hay {CLIP_NAME} en {amap.name}")
        return
    clip.visible = True
    relabel_clip_groups(clip)
    add_or_update_lito_layer(amap, clip)
    mu = find_layer(amap, MUESTRAS_NAME)
    if mu is not None:
        mu.visible = True
        style_muestras_legend_label(mu)
        configure_muestras_labels(mu)
        print(f"  OK {MUESTRAS_NAME} visible")
    rhr = find_layer(amap, RHR_NAME)
    if rhr is not None:
        rhr.visible = True
        print(f"  OK {RHR_NAME} visible")
    if show_structural:
        for name in STRUCTURAL_LEGEND + [LITO_NAME]:
            lyr = find_layer(amap, name)
            if lyr is not None:
                lyr.visible = True
                print(f"  OK {name} visible")
        volc = find_layer(amap, VOLC_NAME)
        if volc is not None:
            try:
                vcim = volc.getDefinition("V3")
                vcim.renderer.label = VOLC_LEGEND_LABEL
                volc.setDefinition(vcim)
            except Exception as ex:
                print(f"  Aviso etiqueta leyenda Volcanes: {ex}")
        fallas = find_layer(amap, FALLAS_NAME)
        if fallas is not None:
            try:
                fcim = fallas.getDefinition("V3")
                rend = fcim.renderer
                rend.isDefaultSymbolVisible = False
                rend.defaultLabel = ""
                fallas.setDefinition(fcim)
            except Exception:
                pass


def main():
    print("=" * 60)
    print("Leyenda: estructuras + litologia + Muestras CVMVF (misma fila)")
    print("=" * 60)

    aprx = arcpy.mp.ArcGISProject(APRX_PATH)

    m1 = aprx.listMaps("Map_Estructural")
    m2 = aprx.listMaps("Mapa_Litologico")
    if m1:
        print("\n[Map_Estructural]")
        configure_map(m1[0], show_structural=True)
    if m2:
        print("\n[Mapa_Litologico]")
        configure_map(m2[0], show_structural=False)

    lyt1 = find_layout(aprx, "1")
    lyt2 = find_layout(aprx, "2")

    if lyt1:
        print("\n[Diseño1]")
        update_layout_legend(lyt1, include_structural=True)
    if lyt2:
        print("\n[Diseño2]")
        update_layout_legend(lyt2, include_structural=False)

    print("\nGuardar APRX")
    try:
        aprx.save()
        print(f"  OK {APRX_PATH}")
    except Exception as ex:
        print(f"  ERROR al guardar: {ex}")
        print("  Cierra ArcGIS Pro SIN guardar y vuelve a ejecutar el script.")
        raise

    print("\nListo. Si Pro tenia el proyecto abierto, cierra SIN guardar y reabre.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        sys.exit(1)
