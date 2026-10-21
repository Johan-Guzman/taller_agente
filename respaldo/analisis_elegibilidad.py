#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Análisis de elegibilidad para los 20 procesos de secop_muestra.json
Usa herramientas.py (consultar_empresa, calcular_indicadores) sin duplicar lógica.
MODO_DATOS=muestra (obligatorio)
"""

import csv
import json
import os
from datetime import datetime
from pathlib import Path

import herramientas as h

BASE = Path(__file__).parent
DATOS = BASE / "datos"
RESULTADOS = BASE / "resultados"
RESULTADOS.mkdir(exist_ok=True)

os.environ["MODO_DATOS"] = "muestra"


def norm_unspsc_code(code):
    if not code:
        return None
    s = str(code).strip().upper()
    # Quitar prefijo V1.
    if s.startswith("V1."):
        s = s[3:]
    # Solo dígitos
    digits = "".join(c for c in s if c.isdigit())
    if not digits:
        return None
    return digits


def unspsc_levels(digits):
    if not digits:
        return {}
    return {
        "segmento": digits[:2] if len(digits) >= 2 else digits,
        "familia": digits[:4] if len(digits) >= 4 else digits,
        "clase": digits[:6] if len(digits) >= 6 else digits,
        "completo": digits,
    }


def match_unspsc(proc_code, emp_codes):
    """Compara a nivel segmento/familia/clase. Retorna (nivel_coincidencia, match_detail)"""
    p_digits = norm_unspsc_code(proc_code)
    if not p_digits or p_digits == "UNSPECIFIED":
        return ("no_verificable", "codigo_principal_de_categoria ausente o UNSPECIFIED")
    
    emp_digits_list = []
    for c in emp_codes or []:
        d = norm_unspsc_code(c)
        if d:
            emp_digits_list.append(d)
    if not emp_digits_list:
        return ("no_verificable", "empresa sin codigos UNSPSC verificables")
    
    p_levels = unspsc_levels(p_digits)
    best = None
    best_detail = None
    for ed in emp_digits_list:
        e_levels = unspsc_levels(ed)
        # Comparar de mayor a menor especificidad
        if p_levels["clase"] == e_levels["clase"] and len(p_levels["clase"]) >= 2:
            best = "clase"
            best_detail = f"coincide clase {p_levels['clase']} con {ed}"
            break
        if best is None and p_levels["familia"] == e_levels["familia"] and len(p_levels["familia"]) >= 2:
            best = "familia"
            best_detail = f"coincide familia {p_levels['familia']} con {ed}"
        elif best != "clase" and p_levels["segmento"] == e_levels["segmento"] and len(p_levels["segmento"]) >= 2 and best is None:
            best = "segmento"
            best_detail = f"coincide segmento {p_levels['segmento']} con {ed}"
    if best:
        return (best, best_detail)
    return ("no_coincide", f"sin coincidencia con {emp_digits_list} (proc={p_digits})")


def is_directa(modalidad):
    m = str(modalidad or "").lower()
    if "contratación directa" in m or "contratacion directa" in m:
        return True
    return False


def is_licitacion_publica(modalidad):
    m = str(modalidad or "").lower()
    if "licitación pública" in m or "licitacion publica" in m or m.strip().startswith("licitaci"):
        return True
    return False


def main():
    empresa = h.consultar_empresa()
    ind = h.calcular_indicadores()  # sin presupuesto proceso
    
    procesos = json.loads((DATOS / "secop_muestra.json").read_text(encoding="utf-8"))
    
    resultados = []
    
    for p in procesos:
        pid = p.get("id_del_proceso") or p.get("referencia_del_proceso")
        ref = p.get("referencia_del_proceso")
        entidad = p.get("entidad")
        objeto = p.get("descripci_n_del_procedimiento") or ""
        modalidad = p.get("modalidad_de_contratacion") or ""
        precio_base = p.get("precio_base")
        try:
            cuantia = float(precio_base) if precio_base not in (None, "", "0") else 0.0
        except Exception:
            cuantia = 0.0
        fecha_pub = p.get("fecha_de_publicacion_del") or ""
        fecha_rec = p.get("fecha_de_recepcion_de") or ""
        estado = p.get("estado_resumen") or ""
        adjudicado = p.get("adjudicado") or ""
        duracion = p.get("duracion")
        unidad_dur = p.get("unidad_de_duracion")
        codigo_cat = p.get("codigo_principal_de_categoria")
        num_resp = p.get("respuestas_al_procedimiento")
        prov = p.get("nombre_del_proveedor")
        val_adj = p.get("valor_total_adjudicacion")
        
        criterios = {}
        evidencias = []
        excluyente = False
        
        # 1. Estado y vigencia
        fecha_ref_usada = "fecha_de_publicacion_del"
        if fecha_rec:
            # Si hay fecha de recepción, puede indicar cierre/plazo de recepción
            fecha_ref_usada = "fecha_de_recepcion_de (comparación con fecha_de_publicacion_del)"
            try:
                fpub = datetime.fromisoformat(str(fecha_pub).replace("Z", "+00:00").replace("T00:00:00.000", ""))
                frec = datetime.fromisoformat(str(fecha_rec).replace("Z", "+00:00").replace("T00:00:00.000", ""))
                if frec < fpub:
                    criterios["estado_vigencia"] = "no_verificable"
                    evidencias.append(f"fecha_de_recepcion_de ({fecha_rec}) anterior a fecha_de_publicacion_del ({fecha_pub}) - inconsistente")
                elif estado.lower() in ["adjudicado", "cerrado", "terminado"]:
                    # aún puede estar cerrado pero ya adjudicado; no es automáticamente excluyente sin fecha futura
                    criterios["estado_vigencia"] = "cumple"
                    evidencias.append(f"estado={estado}, adjudicado={adjudicado}; fecha_ref={fecha_ref_usada}")
                else:
                    criterios["estado_vigencia"] = "cumple"
                    evidencias.append(f"estado={estado}; hay fecha_de_recepcion_de={fecha_rec} (abierto/evaluación/publicado)")
            except Exception:
                criterios["estado_vigencia"] = "no_verificable"
                evidencias.append("no se pudo parsear fechas")
        else:
            if estado.lower() in ["adjudicado"]:
                criterios["estado_vigencia"] = "cumple"  # ya adjudicado pero criterio pide "abierto" - no es excluyente per se; marcar con evidencia
                evidencias.append(f"estado={estado}, adjudicado={adjudicado}; sin fecha_de_recepcion_de - no hay evidencia de cierre expirado")
            elif estado.lower() in ["evaluación", "publicado", "seleccionado"]:
                criterios["estado_vigencia"] = "cumple"
                evidencias.append(f"estado={estado}; sin fecha_de_recepcion_de (fecha_ref usada: {fecha_ref_usada})")
            else:
                criterios["estado_vigencia"] = "no_verificable"
                evidencias.append(f"estado={estado}; sin fecha_de_recepcion_de para verificar vigencia")
        
        # 2. Modalidad
        if is_directa(modalidad):
            criterios["modalidad"] = "no_cumple"
            excluyente = True
            evidencias.append(f"modalidad='{modalidad}' - contratación directa (suele no admitir participación competitiva)")
        elif is_licitacion_publica(modalidad):
            criterios["modalidad"] = "cumple"
            evidencias.append(f"modalidad='{modalidad}' - admite participación")
        elif "selección abreviada" in str(modalidad).lower() or "abreviada" in str(modalidad).lower():
            # Menor cuantía puede tener restricciones; no hay restricción Mipyme explícita en perfil
            criterios["modalidad"] = "cumple"
            evidencias.append(f"modalidad='{modalidad}' - participación posible (sin restricción Mipyme explícita en perfil)")
        elif "régimen especial" in str(modalidad).lower():
            criterios["modalidad"] = "cumple"
            evidencias.append(f"modalidad='{modalidad}' - régimen especial (verificar convocatoria)")
        elif "enajenación" in str(modalidad).lower():
            criterios["modalidad"] = "no_cumple"
            excluyente = True
            evidencias.append(f"modalidad='{modalidad}' - no es proceso de contratación para prestación/suministro/obra")
        else:
            criterios["modalidad"] = "no_verificable"
            evidencias.append(f"modalidad='{modalidad}' - no clasificable con reglas dadas")
        
        # 3. UNSPSC
        unspsc_res, unspsc_det = match_unspsc(codigo_cat, empresa.get("rup", {}).get("codigos_unspsc"))
        if unspsc_res == "no_coincide":
            criterios["unspsc"] = "no_cumple"
            excluyente = True
            evidencias.append(f"UNSPSC: {unspsc_det}")
        elif unspsc_res == "no_verificable":
            criterios["unspsc"] = "no_verificable"
            evidencias.append(f"UNSPSC: {unspsc_det}")
        else:
            criterios["unspsc"] = "cumple"
            evidencias.append(f"UNSPSC: coincide a nivel {unspsc_res} - {unspsc_det}")
        
        # 4. Capacidad financiera
        if cuantia > 0:
            ind_con = h.calcular_indicadores(presupuesto_proceso=cuantia)
            pct_ct = ind_con.get("capital_trabajo_pct_del_presupuesto")
            criterios["capacidad_financiera"] = "cumple" if pct_ct is not None and pct_ct >= 10 else ("no_verificable" if pct_ct is None else "no_cumple")
            evidencias.append(f"Indicadores: liquidez={ind['indice_liquidez']}, endeudamiento={ind['indice_endeudamiento_pct']}%, cobertura_intereses={ind['razon_cobertura_intereses']}, CT=${ind['capital_de_trabajo']:,}, CT/presupuesto={pct_ct}% (usando calcular_indicadores)")
            if pct_ct is not None and pct_ct < 10:
                excluyente = True  # margen muy estrecho/excluyente según criterio
        else:
            criterios["capacidad_financiera"] = "no_verificable"
            evidencias.append("presupuesto_base 0 o ausente - no se puede comparar capacidad financiera")
        
        # 5. Experiencia
        exp_list = empresa.get("experiencia", [])
        exp_relevante = []
        for exp in exp_list:
            exp_codes = exp.get("codigos_unspsc", [])
            exp_match, _ = match_unspsc(codigo_cat, exp_codes)
            if exp_match in ["clase", "familia", "segmento"]:
                exp_relevante.append(exp)
            # También por tipo de objeto aproximado
            elif "mantenimiento" in str(objeto).lower() and "mantenimiento" in str(exp.get("objeto","")).lower():
                exp_relevante.append(exp)
            elif "obra" in str(objeto).lower() and ("puente" in str(exp.get("objeto","")).lower() or "vía" in str(exp.get("objeto","")).lower() or "drenaje" in str(exp.get("objeto","")).lower()):
                exp_relevante.append(exp)
            elif "adecuación" in str(objeto).lower() or "mantenimiento de instalaciones" in str(objeto).lower():
                if "adecuación" in str(exp.get("objeto","")).lower() or "mantenimiento" in str(exp.get("objeto","")).lower() or "instalaciones" in str(exp.get("objeto","")).lower():
                    exp_relevante.append(exp)
        
        if not exp_relevante:
            criterios["experiencia"] = "no_verificable"
            evidencias.append("Sin experiencia claramente relevante por UNSPSC/objeto en los 4 contratos")
        else:
            # Verificar suficiencia vs cuantía
            if cuantia > 0:
                max_exp = max([float(e.get("valor",0)) for e in exp_relevante])
                ratio = max_exp / cuantia if cuantia > 0 else 0
                if ratio >= 0.5:  # al menos 50% del valor
                    criterios["experiencia"] = "cumple"
                    evidencias.append(f"Experiencia relevante: {[e['id'] for e in exp_relevante]} (max ${max_exp:,}, ratio={ratio:.2f}x cuantía)")
                elif ratio >= 0.2:
                    criterios["experiencia"] = "cumple_con_reserva"
                    evidencias.append(f"Experiencia relevante pero valor menor: {[e['id'] for e in exp_relevante]} (max ${max_exp:,}, ratio={ratio:.2f}x cuantía)")
                else:
                    criterios["experiencia"] = "no_cumple"
                    excluyente = True
                    evidencias.append(f"Experiencia relevante insuficiente: {[e['id'] for e in exp_relevante]} (max ${max_exp:,}, ratio={ratio:.2f}x cuantía)")
            else:
                criterios["experiencia"] = "cumple"
                evidencias.append(f"Experiencia relevante: {[e['id'] for e in exp_relevante]} (cuantía no verificable)")
        
        # 6. Cuantía
        if cuantia <= 0:
            criterios["cuantia"] = "no_verificable"
            evidencias.append("precio_base 0 o ausente")
        else:
            pct_ct = None
            try:
                ind_con = h.calcular_indicadores(presupuesto_proceso=cuantia)
                pct_ct = ind_con.get("capital_trabajo_pct_del_presupuesto")
            except Exception:
                pass
            if pct_ct is not None and pct_ct >= 20:
                criterios["cuantia"] = "cumple"
                evidencias.append(f"CT cubre {pct_ct}% del presupuesto (CT=${ind['capital_de_trabajo']:,})")
            elif pct_ct is not None and pct_ct >= 10:
                criterios["cuantia"] = "cumple_con_reserva"
                evidencias.append(f"CT cubre {pct_ct}% del presupuesto - margen estrecho")
            elif pct_ct is not None and pct_ct < 10:
                criterios["cuantia"] = "no_cumple"
                excluyente = True
                evidencias.append(f"CT cubre {pct_ct}% del presupuesto - insuficiente")
            else:
                criterios["cuantia"] = "no_verificable"
                evidencias.append("No se pudo calcular compatibilidad cuantía/capacidad")
        
        # 7. Datos incompletos
        datos_faltantes = []
        if not codigo_cat or codigo_cat == "UNSPECIFIED":
            datos_faltantes.append("codigo_principal_de_categoria")
        if cuantia <= 0:
            datos_faltantes.append("precio_base")
        if not fecha_rec and estado.lower() not in ["adjudicado", "evaluación", "publicado", "seleccionado"]:
            pass  # ya manejado
        if datos_faltantes:
            criterios["datos_incompletos"] = "no_determinable_parcial"
            evidencias.append(f"Datos faltantes: {datos_faltantes}")
        else:
            criterios["datos_incompletos"] = "ok"
        
        # Veredicto
        no_cumple_list = [k for k,v in criterios.items() if v == "no_cumple"]
        no_verif_list = [k for k,v in criterios.items() if v in ["no_verificable", "no_determinable_parcial"]]
        cumple_reserva_list = [k for k,v in criterios.items() if v in ["cumple_con_reserva"]]
        
        if excluyente or no_cumple_list:
            veredicto = "NO PUEDE APLICAR"
            motivo = f"Incumple/excluyente en: {', '.join(no_cumple_list) or 'criterio excluyente'}"
        elif no_verif_list and not no_cumple_list:
            if cumple_reserva_list:
                veredicto = "APLICA CON RESERVAS"
                motivo = f"Verificables ok pero hay no verificables: {', '.join(no_verif_list)}; reservas: {', '.join(cumple_reserva_list)}"
            else:
                veredicto = "NO DETERMINABLE"
                motivo = f"Faltan datos críticos para determinar: {', '.join(no_verif_list)}"
        elif cumple_reserva_list:
            veredicto = "APLICA CON RESERVAS"
            motivo = f"Cumple lo verificable con márgenes estrechos/reservas: {', '.join(cumple_reserva_list)}"
        else:
            # Todos verificables y cumplen
            all_ok = all(v in ["cumple", "ok"] for v in criterios.values())
            if all_ok:
                veredicto = "PUEDE APLICAR"
                motivo = "Cumple todos los criterios verificables"
            else:
                veredicto = "APLICA CON RESERVAS"
                motivo = "Revisar criterios mixtos"
        
        resultados.append({
            "id_proceso": pid,
            "referencia": ref,
            "entidad": entidad,
            "objeto": objeto,
            "modalidad": modalidad,
            "cuantia": cuantia,
            "fecha_publicacion": fecha_pub,
            "fecha_recepcion": fecha_rec,
            "estado": estado,
            "adjudicado": adjudicado,
            "duracion": duracion,
            "unidad_duracion": unidad_dur,
            "codigo_categoria": codigo_cat,
            "respuestas": num_resp,
            "proveedor": prov,
            "valor_adjudicacion": val_adj,
            "criterio_estado_vigencia": criterios.get("estado_vigencia"),
            "criterio_modalidad": criterios.get("modalidad"),
            "criterio_unspsc": criterios.get("unspsc"),
            "criterio_capacidad_financiera": criterios.get("capacidad_financiera"),
            "criterio_experiencia": criterios.get("experiencia"),
            "criterio_cuantia": criterios.get("cuantia"),
            "criterio_datos_incompletos": criterios.get("datos_incompletos"),
            "veredicto": veredicto,
            "motivo_principal": motivo,
            "evidencias": " | ".join(evidencias),
        })
    
    # CSV
    csv_path = RESULTADOS / "elegibilidad.csv"
    fieldnames = [
        "id_proceso", "referencia", "entidad", "objeto", "modalidad", "cuantia", 
        "fecha_publicacion", "fecha_recepcion", "estado", "adjudicado",
        "criterio_estado_vigencia", "criterio_modalidad", "criterio_unspsc", 
        "criterio_capacidad_financiera", "criterio_experiencia", "criterio_cuantia", 
        "criterio_datos_incompletos", "veredicto", "motivo_principal", "evidencias"
    ]
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in resultados:
            row = {k: r.get(k) for k in fieldnames}
            w.writerow(row)
    
    # MD
    md_path = RESULTADOS / "elegibilidad.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Análisis de elegibilidad - Taller 1 (SECOP muestra)\n\n")
        f.write(f"**Empresa:** {empresa['razon_social']}  \n")
        f.write(f"**Fecha análisis:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n")
        f.write(f"**Modo datos:** muestra (MODO_DATOS=muestra)  \n\n")
        f.write("## Indicadores empresa (calcular_indicadores)\n\n")
        f.write(f"- Índice liquidez: {ind['indice_liquidez']}\n")
        f.write(f"- Endeudamiento: {ind['indice_endeudamiento_pct']}%\n")
        f.write(f"- Cobertura intereses: {ind['razon_cobertura_intereses']}\n")
        f.write(f"- Capital de trabajo: ${ind['capital_de_trabajo']:,}\n")
        f.write(f"- Rentabilidad patrimonio: {ind['rentabilidad_patrimonio']}\n")
        f.write(f"- Rentabilidad activo: {ind['rentabilidad_activo']}\n")
        f.write(f"- Corte EE.FF.: {ind['corte_estados_financieros']}\n\n")
        f.write("## Resumen por proceso\n\n")
        f.write("| # | Proceso (ref/id) | Entidad | Modalidad | Cuantía (COP) | Estado/Adj | Estado/Vigencia | Modalidad | UNSPSC | Cap.Financiera | Experiencia | Cuantía | Datos | Veredicto |\n")
        f.write("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n")
        for i,r in enumerate(resultados, 1):
            cuantia_str = f"${r['cuantia']:,.0f}" if r['cuantia'] > 0 else "N/D"
            f.write(f"| {i} | {r['referencia']}<br/>{r['id_proceso']} | {r['entidad'][:40]} | {r['modalidad'][:30]} | {cuantia_str} | {r['estado']}/{r['adjudicado']} | {r['criterio_estado_vigencia']} | {r['criterio_modalidad']} | {r['criterio_unspsc']} | {r['criterio_capacidad_financiera']} | {r['criterio_experiencia']} | {r['criterio_cuantia']} | {r['criterio_datos_incompletos']} | **{r['veredicto']}** |\n")
        f.write("\n## Justificación por proceso\n\n")
        for i,r in enumerate(resultados, 1):
            f.write(f"### {i}. {r['referencia']} ({r['id_proceso']}) - {r['entidad']}\n\n")
            f.write(f"**Objeto:** {r['objeto'][:200]}{'...' if len(r['objeto'])>200 else ''}  \n")
            f.write(f"**Modalidad:** {r['modalidad']} | **Cuantía:** ${r['cuantia']:,.0f} | **Fecha pub:** {r['fecha_publicacion']} | **Fecha recep:** {r['fecha_recepcion'] or 'N/D'} | **Estado:** {r['estado']} | **Adjudicado:** {r['adjudicado']}  \n")
            f.write(f"**Categoría UNSPSC:** {r['codigo_categoria']} | **Respuestas:** {r['respuestas']} | **Proveedor:** {r['proveedor']}  \n\n")
            f.write(f"**Veredicto:** {r['veredicto']}  \n")
            f.write(f"**Motivo principal:** {r['motivo_principal']}  \n\n")
            f.write("**Evidencia / criterios:**  \n")
            for ev in r['evidencias'].split(' | '):
                if ev.strip():
                    f.write(f"- {ev.strip()}  \n")
            f.write("\n---\n\n")
        
        # Resumen
        from collections import Counter
        c = Counter([r['veredicto'] for r in resultados])
        f.write("## Resumen de veredictos\n\n")
        for k,v in c.items():
            f.write(f"- {k}: {v}\n")
        f.write("\n## 3 más prometedores (razón)\n\n")
        # Prometedores: PUEDE APLICAR primero, luego APLICA CON RESERVAS con menos reservas
        prometedores = []
        for r in resultados:
            score = 0
            if r['veredicto'] == 'PUEDE APLICAR':
                score = 100
            elif r['veredicto'] == 'APLICA CON RESERVAS':
                score = 50
            elif r['veredicto'] == 'NO DETERMINABLE':
                score = 10
            else:
                score = 0
            # Menos no verificables mejor
            no_verif = sum(1 for k in ['criterio_estado_vigencia','criterio_modalidad','criterio_unspsc','criterio_capacidad_financiera','criterio_experiencia','criterio_cuantia','criterio_datos_incompletos'] if r[k] in ['no_verificable','no_determinable_parcial'])
            score -= no_verif * 5
            prometedores.append((score, r))
        prometedores.sort(key=lambda x: x[0], reverse=True)
        for idx,(score,r) in enumerate(prometedores[:3], 1):
            f.write(f"{idx}. **{r['referencia']}** ({r['id_proceso']}) - {r['entidad']} | Veredicto: {r['veredicto']} | Cuantía: ${r['cuantia']:,.0f} | Modalidad: {r['modalidad']}  \n")
            f.write(f"   Razón: {r['motivo_principal']}. Evidencia clave: {r['evidencias'][:150]}...  \n\n")
    
    print(f"Generado: {csv_path}")
    print(f"Generado: {md_path}")
    print(f"Total procesos: {len(resultados)}")


if __name__ == "__main__":
    main()
