
import os
import sys
import statistics
from pathlib import Path

from dotenv import load_dotenv
from langsmith import Client

load_dotenv(override=True)

PROJECT_PREFIX = os.getenv("LANGSMITH_PROJECT", "agente-secop")
client = Client()


def obtener_runs(project_name: str) -> list:
    """Obtiene las ejecuciones del proyecto, incluyendo las anidadas."""
    try:
        return list(client.list_runs(project_name=project_name))
    except Exception as exc:
        raise SystemExit(
            f"Error consultando las ejecuciones de '{project_name}': {exc}"
        ) from exc


def es_raiz(run) -> bool:
    """Identifica ejecuciones raíz para contar preguntas."""
    return getattr(run, "parent_run_id", None) is None


def es_llamada_modelo(run) -> bool:
    """Identifica ejecuciones de modelos de lenguaje."""
    return getattr(run, "run_type", None) in ("llm", "chat_model")


def numero(valor) -> float:
    """Convierte valores numéricos ausentes en cero."""
    try:
        return float(valor or 0)
    except (TypeError, ValueError):
        return 0.0


def resumen(prefijo: str) -> dict:
    proyectos = list(
        client.list_projects(
            name_contains=prefijo,
            include_stats=True,
        )
    )

    if not proyectos:
        raise SystemExit(
            f"No hay proyectos de LangSmith con el prefijo '{prefijo}'."
        )

    proyecto = max(
        proyectos,
        key=lambda p: p.start_time or p.id,
    )

    runs = obtener_runs(proyecto.name)
    raices = [r for r in runs if es_raiz(r)]
    modelos = [r for r in runs if es_llamada_modelo(r)]

    # Algunos modelos o integraciones no reportan tokens/costos.
    tokens_in = sum(
        int(numero(getattr(r, "prompt_tokens", 0)))
        for r in modelos
    )
    tokens_out = sum(
        int(numero(getattr(r, "completion_tokens", 0)))
        for r in modelos
    )
    costo = sum(
        numero(getattr(r, "total_cost", 0))
        for r in modelos
    )

    # Latencia de las preguntas completas, no de cada herramienta.
    latencias = sorted(
        (r.end_time - r.start_time).total_seconds()
        for r in raices
        if getattr(r, "end_time", None)
        and getattr(r, "start_time", None)
    )

    p95 = (
        latencias[min(int(0.95 * (len(latencias) - 1)), len(latencias) - 1)]
        if latencias
        else 0
    )

    # Recupera estadísticas de feedback si existen.
    feedback = getattr(proyecto, "feedback_stats", None) or {}
    precision = {}

    for clave, valor in feedback.items():
        if isinstance(valor, dict):
            promedio = valor.get("avg", valor.get("mean"))
            if promedio is not None:
                precision[clave] = round(numero(promedio) * 100, 1)
        elif valor is not None:
            try:
                precision[clave] = round(float(valor) * 100, 1)
            except (TypeError, ValueError):
                pass

    preguntas = len(raices)

    if not modelos:
        print(
            f"AVISO: el proyecto '{proyecto.name}' no contiene "
            "ejecuciones identificadas como llamadas a modelos."
        )

    if modelos and tokens_in == 0 and tokens_out == 0:
        print(
            f"AVISO: '{proyecto.name}' tiene ejecuciones de modelo, "
            "pero no reporta tokens. Revisa los metadatos de uso."
        )

    return {
        "experimento": proyecto.name,
        "preguntas": preguntas,
        "precision": precision,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "tokens_total": tokens_in + tokens_out,
        "costo_total": costo,
        "costo_pregunta": costo / preguntas if preguntas else 0,
        "lat_p50": statistics.median(latencias) if latencias else 0,
        "lat_p95": p95,
        "total_runs": len(runs),
        "runs_modelo": len(modelos),
    }


def tabla(filas: list[dict]) -> str:
    claves = sorted({
        clave
        for fila in filas
        for clave in fila.get("precision", {})
    })

    cabecera = (
        ["Experimento", "Preg.", "Ejecuciones", "Llamadas modelo"]
        + [f"Prec. {clave} %" for clave in claves]
        + [
            "Tokens in",
            "Tokens out",
            "Tokens total",
            "Costo USD",
            "USD/preg.",
            "Lat. p50 s",
            "Lat. p95 s",
        ]
    )

    salida = [
        "| " + " | ".join(cabecera) + " |",
        "|" + "---|" * len(cabecera),
    ]

    for fila in filas:
        precision = fila.get("precision", {})

        celdas = (
            [
                fila["experimento"],
                str(fila["preguntas"]),
                str(fila["total_runs"]),
                str(fila["runs_modelo"]),
            ]
            + [str(precision.get(clave, "-")) for clave in claves]
            + [
                f'{fila["tokens_in"]:,}',
                f'{fila["tokens_out"]:,}',
                f'{fila["tokens_total"]:,}',
                f'{fila["costo_total"]:.6f}',
                f'{fila["costo_pregunta"]:.6f}',
                f'{fila["lat_p50"]:.2f}',
                f'{fila["lat_p95"]:.2f}',
            ]
        )

        salida.append("| " + " | ".join(celdas) + " |")

    return "\n".join(salida)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(
            "Uso: python costos.py <prefijo1> [<prefijo2> ...]\n"
            f"Proyecto configurado por defecto: {PROJECT_PREFIX}"
        )

    filas = [resumen(prefijo) for prefijo in sys.argv[1:]]
    markdown = tabla(filas)

    print(markdown)

    Path("resultados").mkdir(exist_ok=True)
    Path("resultados/resumen_costos.md").write_text(
        markdown,
        encoding="utf-8",
    )

    print("\nGuardado en resultados/resumen_costos.md")
