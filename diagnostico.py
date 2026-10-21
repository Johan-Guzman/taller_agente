
from dotenv import load_dotenv
from langsmith import Client

load_dotenv(override=True)
client = Client()

for nombre in ("A-linea-base-33b01cd5", "B-elegibilidad-080de3c1"):
    print(f"\n{'=' * 70}\nPROYECTO: {nombre}\n{'=' * 70}")

    runs = client.list_runs(
        project_name=nombre,
        run_type="llm",
    )

    for i, r in enumerate(runs):
        if i >= 3:
            break

        print({
            "nombre": r.name,
            "tipo": r.run_type,
            "modelo": getattr(r, "extra", None),
            "prompt_tokens": getattr(r, "prompt_tokens", None),
            "completion_tokens": getattr(r, "completion_tokens", None),
            "total_cost": str(getattr(r, "total_cost", None)),
            "inputs": getattr(r, "inputs", None),
            "outputs": getattr(r, "outputs", None),
        })
