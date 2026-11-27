"""Evaluación geométrica de cabezas contra glifos vectoriales del PDF original.

Este módulo es exclusivamente de evaluación. No alimenta ni modifica el
reconocimiento OMR. Solo es válido cuando la fuente musical del PDF tiene
un mapa de glifos conocido y revisado (por ejemplo, RepriseStd / œ).
"""
from __future__ import annotations
from collections.abc import Mapping, Sequence
from hashlib import sha256
import json, math
from pathlib import Path
from typing import Any
import fitz

def _glyph_centers(page: fitz.Page, font_name: str, glyph_char: str) -> list[tuple[float,float]]:
    centers=[]
    raw=page.get_text("rawdict")
    for block in raw.get("blocks",[]):
        for line in block.get("lines",[]):
            for span in line.get("spans",[]):
                if span.get("font")!=font_name: continue
                for char in span.get("chars",[]):
                    if char.get("c")!=glyph_char: continue
                    x0,y0,x1,y1=char["bbox"]; centers.append(((x0+x1)/2,(y0+y1)/2))
    return centers

def _maximum_cardinality_matches(predictions: Sequence[tuple[float,float]], references: Sequence[tuple[float,float]], tolerance: float) -> list[tuple[int,int,float]]:
    neighbors=[]
    for px,py in predictions:
        options=[]
        for ref_index,(rx,ry) in enumerate(references):
            distance=math.hypot(px-rx,py-ry)
            if distance<=tolerance: options.append((distance,ref_index))
        neighbors.append(sorted(options))
    order=sorted(range(len(predictions)),key=lambda i:(len(neighbors[i]),i))
    reference_to_prediction={}
    def assign(prediction_index,visited):
        for distance,reference_index in neighbors[prediction_index]:
            if reference_index in visited: continue
            visited.add(reference_index)
            previous=reference_to_prediction.get(reference_index)
            if previous is None or assign(previous[0],visited):
                reference_to_prediction[reference_index]=(prediction_index,distance); return True
        return False
    for prediction_index in order: assign(prediction_index,set())
    return sorted(((pi,ri,d) for ri,(pi,d) in reference_to_prediction.items()),key=lambda item:item[0])

def _metrics(predicted_count:int,reference_count:int,matches:int)->dict[str,Any]:
    fp=predicted_count-matches; fn=reference_count-matches
    precision=matches/predicted_count if predicted_count else None
    recall=matches/reference_count if reference_count else None
    f1=2*precision*recall/(precision+recall) if precision is not None and recall is not None and precision+recall else None
    return {"predicted_count":predicted_count,"reference_count":reference_count,"true_positive":matches,"false_positive":fp,"false_negative":fn,"precision":precision,"recall":recall,"f1":f1}

def evaluate_pdf_glyph_noteheads(pdf_path:str|Path,analysis:Mapping[str,Any]|str|Path,*,tolerance_points:float=3.0,font_name:str="RepriseStd",glyph_char:str="œ")->dict[str,Any]:
    """Compara candidatos OMR con glifos notehead del texto vectorial del PDF."""
    path=Path(pdf_path)
    if not path.is_file(): raise ValueError(f"No existe el PDF: {path}")
    if not isinstance(tolerance_points,(int,float)) or isinstance(tolerance_points,bool) or not math.isfinite(tolerance_points) or tolerance_points<=0: raise ValueError("tolerance_points debe ser positivo y finito")
    if not isinstance(font_name,str) or not font_name.strip(): raise ValueError("font_name debe ser texto no vacío")
    if not isinstance(glyph_char,str) or len(glyph_char)!=1: raise ValueError("glyph_char debe contener exactamente un carácter")
    data=json.loads(Path(analysis).read_text(encoding="utf-8")) if isinstance(analysis,(str,Path)) else dict(analysis)
    pages=data.get("pages")
    if not isinstance(pages,list) or not pages: raise ValueError("analysis debe contener una lista pages no vacía")
    dpi=pages[0].get("render_dpi")
    if not isinstance(dpi,(int,float)) or isinstance(dpi,bool) or dpi<=0: raise ValueError("analysis debe incluir render_dpi positivo")
    scale=float(dpi)/72.0; digest=sha256(path.read_bytes()).hexdigest()
    results=[]; total_pred=total_ref=total_match=0; all_dist=[]
    with fitz.open(path) as document:
        if len(document)!=len(pages): raise ValueError("El número de páginas del PDF y analysis no coincide")
        for page_index,(pdf_page,page_data) in enumerate(zip(document,pages),start=1):
            if page_data.get("page_number")!=page_index: raise ValueError("Las páginas de analysis deben estar ordenadas y numeradas desde 1")
            refs=_glyph_centers(pdf_page,font_name,glyph_char)
            items=list(page_data.get("notehead_candidates",[]))+list(page_data.get("hollow_notehead_candidates",[]))
            preds=[(float(item["center_x"])/scale,float(item["center_y"])/scale) for item in items]
            matches=_maximum_cardinality_matches(preds,refs,float(tolerance_points))
            metrics=_metrics(len(preds),len(refs),len(matches)); distances=[item[2] for item in matches]; all_dist.extend(distances)
            results.append({"page_number":page_index,**metrics,"mean_matched_center_error_points":sum(distances)/len(distances) if distances else None})
            total_pred+=len(preds); total_ref+=len(refs); total_match+=len(matches)
    return {"evaluation_type":"pdf_embedded_glyph_notehead_geometry","source_pdf":path.name,"source_sha256":digest,"page_count":len(results),"reference_font":font_name,"reference_glyph":glyph_char,"tolerance_points":float(tolerance_points),**_metrics(total_pred,total_ref,total_match),"mean_matched_center_error_points":sum(all_dist)/len(all_dist) if all_dist else None,"pages":results,"limitations":["Solo evalúa localización de cabezas contra glifos vectoriales del PDF.","No mide notas omitidas que no estén representadas por el glifo configurado.","No mide alturas, alteraciones, figuras, duraciones, silencios, voces ni polifonía.","No es una métrica de precisión musical global ni una validación de partituras escaneadas.","El mapa de fuente y glifo de referencia debe verificarse para cada familia tipográfica."]}
