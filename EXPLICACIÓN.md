# Taller 1 · Agente analista del SECOP

Equipo: Guzmán · Grajales

## 1. Qué buscábamos

El taller pide un agente con al menos dos herramientas propias que decida solo cuándo usarlas, con trazas en LangSmith, y que llegue al **85 % de precisión con el menor costo posible**.

Nosotros lo enfocamos en una pregunta concreta: **de los 20 procesos de SECOP II de la muestra, ¿a cuáles puede presentarse nuestra empresa ficticia y a cuáles no?** Además mejoramos el agente para que responda "¿puede la empresa aplicar al proceso X?" mirando criterio por criterio y diciendo qué datos le faltan en lugar de inventarlos.

## 2. Qué hicimos

Partimos del agente base del taller (`agente.py`, `herramientas.py`, `evaluar.py`) y trabajamos en tres frentes.

**Mejoramos el agente (`agente.py`).**
- Reescribimos las descripciones de las tres herramientas (`buscar_procesos`, `consultar_empresa`, `calcular_indicadores`) para que el modelo sepa cuándo usar cada una y qué campos trae.
- Reescribimos el prompt del sistema. Ahora le exige citar el proceso (referencia o id), no inventar cifras, decir "no verificable" cuando falta un dato y seguir siempre este orden: buscar el proceso, consultar la empresa, calcular indicadores, evaluar criterio por criterio y dar un veredicto.

**Analizamos los 20 procesos (`analisis_elegibilidad.py`).**
Es un script que reutiliza las funciones de `herramientas.py` (no duplicamos lógica) y evalúa cada proceso con siete criterios: estado y vigencia, modalidad, códigos UNSPSC, capacidad financiera, experiencia, cuantía y datos incompletos. Cada proceso termina en uno de cuatro veredictos: PUEDE APLICAR, APLICA CON RESERVAS, NO PUEDE APLICAR o NO DETERMINABLE. Genera `resultados/elegibilidad.csv` y `resultados/elegibilidad.md`.

**Medimos costos (`costos.py`).**
Lee de LangSmith los experimentos y calcula precisión, tokens, costo total, costo por pregunta y latencia. Guarda la tabla en `resultados/resumen_costos.md`.

No tocamos `datos/conjunto_referencia.json`, `datos/secop_muestra.json` ni `datos/empresa.json`. Antes de editar guardamos copia de los archivos en `respaldo/`.

## 3. Por qué lo hicimos así

- **Tres herramientas y no más.** Cada una cubre una fuente distinta: los procesos, el perfil de la empresa y los indicadores financieros. Con eso se puede comparar un proceso contra la empresa sin agregar piezas que subirían el costo.
- **El prompt manda sobre la herramienta.** Vimos que el agente base respondía de forma genérica. Obligarlo a seguir un orden y a citar el proceso nos pareció la mejora más barata, porque no cambia el modelo ni agrega llamadas.
- **No inventar umbrales.** Los pliegos completos están en PDF y eso se resuelve en el Taller 2 con RAG. Por eso, cuando un requisito no aparece en los datos del JSON, el agente lo marca como no verificable.
- **Modelo: `claude-haiku-5-5`.** Es el modelo pequeño que usamos en ambos experimentos. Todavía no lo comparamos con un modelo más grande, así que no podemos afirmar que sea la mejor relación costo-precisión, solo que es barato y que con él se cumple lo que medimos (ver sección 4).

## 4. Resultados

### 4.1 Elegibilidad de los 20 procesos

| # | Proceso | Entidad | Modalidad | Cuantía (COP) | Veredicto | Motivo principal |
|---|---|---|---|---|---|---|
| 1 | CO1.REQ.2577563 | DANE | Contratación directa | 57.333.333 | NO PUEDE | Modalidad |
| 2 | CO1.REQ.2085169 | Distrito de Barranquilla | Contratación directa | 2.917.200.000 | NO PUEDE | Modalidad |
| 3 | CO1.REQ.7128715 | Colegio Gabriel Betancourt Mejía | Régimen especial (con ofertas) | 5.500.000 | NO PUEDE | UNSPSC |
| 4 | CO1.REQ.9845111 | INVIAS | Contratación directa | 48.620.250 | NO PUEDE | Modalidad |
| 5 | CO1.REQ.8273274 | Mpio. San Miguel (Putumayo) | Contratación directa | 10.000.000 | NO PUEDE | Modalidad |
| 6 | CO1.REQ.4098730 | Mpio. Piedecuesta | Contratación directa | 12.000.000 | NO PUEDE | Modalidad |
| 7 | CO1.REQ.6622657 | AGROSAVIA | Régimen especial | 0 | NO PUEDE | UNSPSC |
| 8 | CO1.REQ.9182530 | ESE Bellosalud | Régimen especial | 4.260.200 | NO PUEDE | UNSPSC |
| 9 | CO1.REQ.5610848 | Sec. Distrital de Integración Social | Contratación directa | 53.579.880 | NO PUEDE | Modalidad |
| 10 | CO1.REQ.1780926 | ESAP Boyacá-Casanare | Contratación directa | 9.108.000 | NO PUEDE | Modalidad |
| 11 | CO1.REQ.848621 | Alcaldía Local de Sumapaz | Licitación pública (obra) | 600.000.000 | **PUEDE APLICAR** | Cumple lo verificable |
| 12 | CO1.REQ.1892979 | Fondo Nacional de Vivienda | Contratación directa | 448.000.000 | NO PUEDE | Modalidad |
| 13 | CO1.REQ.976985 | INVIAS | Licitación pública (obra) | 53.520.784.298 | NO PUEDE | Cuantía |
| 14 | CO1.REQ.9500237 | Alcaldía de Floridablanca | Selección abreviada menor cuantía | 305.813.941 | NO DETERMINABLE | UNSPSC sin especificar |
| 15 | CO1.REQ.4389286 | IDEPORTES Medellín | Selección abreviada subasta inversa | 270.101.513 | NO PUEDE | UNSPSC |
| 16 | CO1.REQ.6085225 | Gobernación del Chocó | Contratación directa | 24.000.000 | NO PUEDE | Modalidad |
| 17 | CO1.REQ.4114873 | Alcaldía de Girardota | Enajenación con subasta | 86.000.000 | NO PUEDE | Modalidad |
| 18 | CO1.REQ.7180132 | ESE Carmen Emilia Ospina | Régimen especial | 320.000.000 | NO PUEDE | UNSPSC |
| 19 | CO1.REQ.7095796 | ESE Cxayuce Jxut | Régimen especial | 21.280.000 | NO PUEDE | UNSPSC |
| 20 | CO1.REQ.10651936 | I.E. Las Colinas | Régimen especial | 5.400.000 | NO PUEDE | UNSPSC |

**Conteo:** 1 PUEDE APLICAR · 0 CON RESERVAS · 18 NO PUEDE APLICAR · 1 NO DETERMINABLE.

El detalle de cada criterio está en `resultados/elegibilidad.csv`.

**Cómo leer la tabla.** La mayoría de exclusiones son por modalidad: la contratación directa no recibe ofertas, así que no hay a qué presentarse. El único proceso claramente aplicable es el 11 (licitación pública de obra, Sumapaz), con coincidencia de UNSPSC a nivel de familia. El 14 (Floridablanca) se ve prometedor en lo financiero, pero su código UNSPSC viene como `UNSPECIFIED`, así que sin el pliego no se puede decidir.

**Control de consistencia.** Cruzamos el análisis con tres preguntas del conjunto de referencia y coinciden: liquidez de 1,7 (R04), experiencia en UNSPSC 81101500 que suma $950 millones con EXP-1 y EXP-2 (R06), y capital de trabajo de $182 millones equivalente al 59,5 % del 40 % del presupuesto de FLO-INFRA-SA-MC-007-2025 (R16).

### 4.2 Comparación de configuraciones

| | A · Línea base | B · Elegibilidad |
|---|---|---|
| Experimento en LangSmith | `A-linea-base-33b01cd5` | `B-elegibilidad-080de3c1` |
| Modelo | `anthropic:claude-haiku-5-5` | `anthropic:claude-haiku-5-5` |
| Cambio | Prompt y descripciones originales | Prompt con flujo de elegibilidad y descripciones detalladas |
| Uso correcto de herramientas | **[completar tras repetir A]** | 100 % (18/18) |
| Precisión de la respuesta | **[completar]** | **[completar]** |
| Tokens (entrada / salida) | **[completar]** | 163.983 / 11.780 |
| Costo total | **[completar]** | USD 0,0223 |
| Costo por pregunta | **[completar]** | USD 0,00124 |
| Latencia p50 | **[completar]** | 4,5 s |

**Dos advertencias sobre estos números.**

1. La corrida A salió con tokens y costo en cero y con errores en los evaluadores. Coincidió con un conflicto en el `.env` entre `LANGSMITH_PROJECT` y `LANGSMITH_AGENT_ID` / `LANGSMITH_AGENT_ENVIRONMENT`, que impedía registrar trazas. Por eso A **no sirve todavía como comparación**: hay que repetirla con el `.env` corregido (ver sección 6).
2. Del experimento B solo tenemos el evaluador de uso de herramientas. El 100 % significa que el agente eligió las herramientas esperadas, no que todas las respuestas sean correctas. Para afirmar el 85 % de precisión necesitamos también el resultado del evaluador de respuesta correcta.

## 5. Limitaciones

- Muchos requisitos (índices financieros exigidos, experiencia mínima, capacidad de contratación) solo están en los PDF de los pliegos. Con el JSON no se pueden verificar y quedan como no verificables. Se resuelven en el Taller 2 con RAG.
- Algunos procesos traen el código UNSPSC como `UNSPECIFIED` o en un formato que no coincide con el RUP.
- No todos los procesos tienen fecha de cierre; varios de los que sí la tienen ya vencieron (por ejemplo 2019 y 2023). El análisis es un ejercicio sobre la muestra y no una recomendación para presentarse hoy.
- Las restricciones tipo Mipyme limitada no aparecen en los datos del JSON.

## 6. Cómo usarlo y probarlo

Todos los comandos son para PowerShell, desde la carpeta del proyecto.

**1. Configurar `.env`.** Copiar `.env.example` a `.env` y completar:

```env
ANTHROPIC_API_KEY=...
MODELO=anthropic:claude-haiku-5-5
MODO_DATOS=muestra
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=...
LANGSMITH_PROJECT=secop-taller1-Guzman-Grajales
```

Importante: no dejar activas las variables `LANGSMITH_AGENT_ID` ni `LANGSMITH_AGENT_ENVIRONMENT` junto con `LANGSMITH_PROJECT`. Si están las dos, LangSmith no registra ninguna traza. Si quedaron en la sesión, se limpian con:

```powershell
Remove-Item Env:LANGSMITH_AGENT_ID -ErrorAction SilentlyContinue
Remove-Item Env:LANGSMITH_AGENT_ENVIRONMENT -ErrorAction SilentlyContinue
```

**2. Probar las herramientas sin modelo.**

```powershell
.\.venv\Scripts\python.exe herramientas.py
```

Debe mostrar los indicadores de la empresa y un resumen de procesos de licitación.

**3. Probar el agente.**

```powershell
.\.venv\Scripts\python.exe agente.py "¿Cuál es nuestro índice de liquidez?"
.\.venv\Scripts\python.exe agente.py "¿Puede la empresa aplicar al proceso LP-DT-CAU-003-2019?"
```

La primera debe responder 1,7 usando `calcular_indicadores` y sin mensajes de error de LangSmith. La segunda debe buscar el proceso, consultar la empresa, calcular indicadores y dar un veredicto citando el proceso y los datos que faltan.

**4. Generar el análisis de los 20 procesos.**

```powershell
.\.venv\Scripts\python.exe analisis_elegibilidad.py
```

Crea `resultados/elegibilidad.csv` y `resultados/elegibilidad.md`.

**5. Correr y comparar los experimentos.**

```powershell
.\.venv\Scripts\python.exe evaluar.py "A-linea-base"
.\.venv\Scripts\python.exe evaluar.py "B-elegibilidad"
.\.venv\Scripts\python.exe costos.py A-linea-base B-elegibilidad
```

Para que A sea una línea base real, hay que correrla con el prompt y las descripciones originales, que están en `respaldo/agente.py`. Se copia ese archivo sobre `agente.py` (guardando antes la versión mejorada), se corre A y se restaura la versión mejorada para correr B. `costos.py` imprime la tabla y la guarda en `resultados/resumen_costos.md`.

**6. Ver las trazas.** En smith.langchain.com, dentro del proyecto `secop-taller1-Guzman-Grajales`, o en *Datasets & Experiments* → dataset `secop-taller1-referencia` (18 preguntas). Ahí se ven tokens, costo, latencia y feedback por pregunta.

## 7. Conclusión

Con el agente mejorado y `claude-haiku-5-5` el costo es de unos USD 0,0012 por pregunta, es decir, alrededor de **USD 1,24 por cada 1.000 consultas**, y el agente usa las herramientas correctas en las 18 preguntas del conjunto de referencia. Falta cerrar dos cosas para sostener el criterio del 85 %: repetir la línea base con las trazas funcionando y confirmar la precisión de las respuestas. Si esa precisión no llega al 85 %, el siguiente paso sería probar un modelo más grande y comparar el costo adicional.