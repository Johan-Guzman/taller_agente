"""Agente analista del SECOP - Taller 1 (mejorado).

Uso:  python agente.py "¿Puede la empresa aplicar al proceso LP-DT-CAU-003-2019?"
"""
import os
import sys

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.tools import tool

import herramientas as h

load_dotenv()


@tool
def buscar_procesos(entidad: str = None, departamento: str = None, ciudad: str = None,
                    modalidad: str = None, texto: str = None,
                    precio_min: float = None, precio_max: float = None,
                    fecha_desde: str = None, fecha_hasta: str = None,
                    limite: int = 20) -> dict:
    """Busca procesos de contratación pública SECOP II (MODO_DATOS=muestra por defecto).
    Usa filtros precisos: entidad, departamento, ciudad, modalidad (ej. 'licitación pública',
    'contratación directa', 'selección abreviada'), texto en descripción, rango presupuesto
    (COP), fechas publicación AAAA-MM-DD. Siempre cita id_del_proceso/referencia_del_proceso
    cuando respondas sobre un proceso específico."""
    return h.buscar_procesos(entidad, departamento, ciudad, modalidad, texto,
                             precio_min, precio_max, fecha_desde, fecha_hasta, limite)


@tool
def consultar_empresa() -> dict:
    """Consulta el perfil completo de NUESTRA empresa (Ingeniería y Mantenimiento del Pacífico S.A.S.).
    Devuelve: razón social, NIT, ciudad/departamento, tamaño, actividad, RUP (vigente/fecha_renovación,
    códigos UNSPSC), estados financieros (activo/pasivo/patrimonio/utilidad/gastos intereses/corte/moneda),
    y experiencia[] con id, contratante, objeto, año, valor, códigos UNSPSC. Úsalo SIEMPRE para
    evaluar elegibilidad: comparar UNSPSC, capacidad financiera y experiencia relevante."""
    return h.consultar_empresa()


@tool
def calcular_indicadores(presupuesto_proceso: float = None) -> dict:
    """Calcula indicadores financieros de NUESTRA empresa usando datos del RUP/estados financieros.
    Siempre calcula: índice_liquidez, índice_endeudamiento_pct, razón_cobertura_intereses,
    capital_de_trabajo, rentabilidad_patrimonio, rentabilidad_activo, corte_estados_financieros.
    Si se pasa presupuesto_proceso (precio_base del proceso en COP), calcula también
    capital_trabajo_pct_del_presupuesto. NO inventes cifras: usa solo lo que devuelve esta función."""
    return h.calcular_indicadores(presupuesto_proceso)


PROMPT = """Eres un analista estricto de contratación pública colombiana que asesora a "Ingeniería y Mantenimiento del Pacífico S.A.S." (empresa de obras civiles/mantenimiento).

REGLAS INQUEBRANTABLES:
- Responde SIEMPRE en español, breve y preciso.
- Usa MODO_DATOS=muestra. Los datos son los 20 procesos locales.
- NO inventes cifras, umbrales, requisitos o fechas. Si un dato no está en los datos del proceso o en el perfil de la empresa, dilo EXPLÍCITAMENTE: "dato no disponible" / "no verificable".
- Nunca imprimas ni escribas claves de API.
- Cita SIEMPRE el número/referencia del proceso cuando hables de uno específico (ej. LP-DT-CAU-003-2019, id_del_proceso).
- Si hay inconsistencia (plazo 0 días, presupuesto $0, etc.), menciónala explícitamente.

PARA PREGUNTAS DE ELEGIBILIDAD ("¿Puede la empresa aplicar al proceso X?"):
1. BUSCA el proceso con buscar_procesos (por referencia/texto) para obtener todos sus campos reales.
2. CONSULTA el perfil con consultar_empresa() para tener RUP/UNSPSC/EE.FF./experiencia.
3. CALCULA indicadores con calcular_indicadores(presupuesto_proceso=precio_base) para capacidad financiera.
4. EVALÚA CRITERIO POR CRITERIO:
   - Estado y vigencia: estado_resumen, fecha_de_publicacion_del, fecha_de_recepcion_de, adjudicado. Indica qué fecha usaste.
   - Modalidad: modalidad_de_contratacion. Descarta/advierte si es contratación directa, enajenación, o con restricciones. Si no hay restricción explícita, dilo.
   - UNSPSC: compara codigo_principal_de_categoria con codigos_unspsc del RUP a nivel segmento/familia/clase. Indica nivel de coincidencia.
   - Capacidad financiera: usa indicadores calculados vs presupuesto si existe. Si proceso no publica requisitos financieros, indícalo explícitamente.
   - Experiencia: revisa los 4 contratos. ¿Alguno relevante por objeto/UNSPSC? ¿Valor suficiente vs cuantía? Indica proporción/SMMLV si hay datos.
   - Cuantía: compatibilidad con capital de trabajo/patrimonio/capacidad RUP si aplica.
   - Datos incompletos: si faltan campos clave, NO asumas. Clasifica como "no determinable" y di qué dato falta.
5. EMITE VEREDICTO: PUEDE APLICAR | APLICA CON RESERVAS | NO PUEDE APLICAR | NO DETERMINABLE. Justifica con valores usados y cita el proceso.

Usa las herramientas solo cuando necesites datos; preguntas generales respóndelas directamente."""


MODELO = os.getenv("MODELO", "anthropic:claude-haiku-5-5")
agente = create_agent(MODELO, tools=[buscar_procesos, consultar_empresa, calcular_indicadores],
                      system_prompt=PROMPT)


def preguntar(pregunta: str) -> dict:
    """Ejecuta el agente y devuelve la respuesta final y las herramientas que usó."""
    resultado = agente.invoke({"messages": [{"role": "user", "content": pregunta}]})
    usadas = []
    for m in resultado["messages"]:
        tc = getattr(m, "tool_calls", None)
        if tc:
            for t in tc:
                name = t.get("name") if isinstance(t, dict) else getattr(t, "name", None)
                if name:
                    usadas.append(name)
    return {"respuesta": resultado["messages"][-1].content, "herramientas": usadas}


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "¿Cuál es nuestro índice de liquidez?"
    r = preguntar(q)
    print(r["respuesta"])
    print("\nHerramientas usadas:", r["herramientas"] or "ninguna")
