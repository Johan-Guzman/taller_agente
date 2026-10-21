import sys, statistics
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
from langsmith import Client

client = Client()


def resumen(prefijo: str) -> dict:
    proyectos = list(client.list_projects(name_contains=prefijo, include_stats=True))
    if not proyectos:
        raise SystemExit(f"No hay experimentos con prefijo '{prefijo}'")
    p = max(proyectos, key=lambda x: x.start_time)
    try:
        runs = list(client.list_runs(project_name=p.name, is_root=True))
    except Exception:
        runs = []
    n = len(runs) or 1
    costo = sum(float(getattr(r, 'total_cost', 0) or 0) for r in runs)
    t_in = sum(getattr(r, 'prompt_tokens', 0) or 0 for r in runs)
    t_out = sum(getattr(r, 'completion_tokens', 0) or 0 for r in runs)
    lat = sorted((r.end_time - r.start_time).total_seconds() for r in runs if getattr(r, 'end_time', None) and getattr(r, 'start_time', None))
    p95 = lat[int(0.95 * (len(lat) - 1))] if lat else 0
    fb = getattr(p, 'feedback_stats', None) or {}
    precision = {}
    for k, v in fb.items():
        if isinstance(v, dict):
            avg = v.get("avg")
            if avg is None:
                avg = v.get("mean")
            if avg is not None:
                try:
                    precision[k] = round(float(avg) * 100, 1)
                    continue
                except Exception:
                    pass
            # Si no hay avg pero hay valores
            vals = v.get("values") or {}
            if vals:
                try:
                    # intentar promedio de valores numéricos
                    total = 0
                    count = 0
                    for kk, vv in vals.items():
                        if isinstance(vv, dict):
                            total += float(vv.get("count", 0)) * float(vv.get("avg", vv.get("value", 0)))
                            count += int(vv.get("count", 0))
                    if count > 0:
                        precision[k] = round((total / count) * 100, 1)
                        continue
                except Exception:
                    pass
        try:
            if v is not None and not isinstance(v, dict):
                precision[k] = round(float(v) * 100, 1)
        except Exception:
            pass
    return {
        "experimento": p.name,
        "preguntas": n,
        "precision": precision,
        "tokens_in": t_in,
        "tokens_out": t_out,
        "tokens_total": t_in + t_out,
        "costo_total": costo,
        "costo_pregunta": costo / n,
        "lat_p50": statistics.median(lat) if lat else 0,
        "lat_p95": p95,
    }


def tabla(filas: list[dict]) -> str:
    claves = sorted({k for f in filas for k in f.get("precision", {})})
    cab = ["Experimento", "Preg."] + [f"Prec. {k} %" for k in claves] + \
          ["Tokens in", "Tokens out", "Tokens total", "Costo USD", "USD/preg.", "Lat. p50 s", "Lat. p95 s"]
    out = ["| " + " | ".join(cab) + " |", "|" + "---|" * len(cab)]
    for f in filas:
        prec = f.get("precision", {})
        out.append("| " + " | ".join(
            [f.get("experimento", ""), str(f.get("preguntas", ""))]
            + [str(prec.get(k, "-")) for k in claves]
            + [f"{f.get('tokens_in', 0):,}", f"{f.get('tokens_out', 0):,}",
               f"{f.get('tokens_total', 0):,}",
               f"{f.get('costo_total', 0):.6f}", f"{f.get('costo_pregunta', 0):.6f}",
               f"{f.get('lat_p50', 0):.2f}", f"{f.get('lat_p95', 0):.2f}"]) + " |")
    return "\n".join(out)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("Uso: python costos.py <prefijo1> [<prefijo2> ...]")
    filas = [resumen(a) for a in sys.argv[1:]]
    md = tabla(filas)
    print(md)
    Path("resultados").mkdir(exist_ok=True)
    Path("resultados/resumen_costos.md").write_text(md, encoding="utf-8")
    print("\nGuardado en resultados/resumen_costos.md")
