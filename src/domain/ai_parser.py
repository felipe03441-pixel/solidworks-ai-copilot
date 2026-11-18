import os
import re
from dotenv import load_dotenv
from google import genai
from google.genai import types
from src.domain.models import EspecificacionBuje, MaterialMecanizado

load_dotenv(override=True)

SYSTEM_PROMPT = """
Eres un ingeniero mecánico experto en diseño CAD (SolidWorks) y procesos de mecanizado en torno.
Tu única tarea es interpretar solicitudes en lenguaje natural y extraer los parámetros geométricos
y de material exactos para fabricar un buje cilíndrico.

Reglas estrictas:
1. Convierte todas las medidas a milímetros (mm). Si el usuario da pulgadas (ej. 2 pulgadas), convierte exactamente (1 pulgada = 25.4 mm).
2. Si el usuario no especifica el material, asume Bronce SAE 660.
3. Si el usuario no especifica chaflán, asume 1.0 mm.
4. Genera un nombre_pieza limpio sin espacios ni tildes (usa guiones bajos, ej: Buje_Bronce_50x25).
"""

# Solo 2 modelos de clústeres distintos para no bloquear al usuario en caídas globales
MODELOS_RESPALDO = [
    "gemini-3.6-flash",
    "gemini-3.1-flash-lite",
]


def _parser_local_emergencia(texto: str) -> EspecificacionBuje:
    """
    Extractor determinista local (Regex) que responde en <1 ms cuando
    los servidores de Google Gemini están saturados (Error 503 / Timeout).
    """
    texto_lower = texto.lower()

    material = MaterialMecanizado.BRONCE_SAE_660
    if "1045" in texto_lower or "acero" in texto_lower:
        material = MaterialMecanizado.ACERO_1045
    elif "inox" in texto_lower or "304" in texto_lower:
        material = MaterialMecanizado.ACERO_INOX_304
    elif "aluminio" in texto_lower or "6061" in texto_lower:
        material = MaterialMecanizado.ALUMINIO_6061
    elif "nylon" in texto_lower:
        material = MaterialMecanizado.NYLON_6

    factor = 25.4 if "pulgada" in texto_lower else 1.0
    numeros = [float(n) for n in re.findall(r"\d+(?:\.\d+)?", texto_lower)]
    medidas = [n for n in numeros if n not in (1045, 660, 304, 6061)]

    od = round(medidas[0] * factor, 2) if len(medidas) > 0 else 50.0
    id_val = round(medidas[1] * factor, 2) if len(medidas) > 1 else 25.0
    largo = round(medidas[2], 2) if len(medidas) > 2 else 60.0
    chaflan = round(medidas[3], 2) if len(medidas) > 3 else 1.0

    nombre = f"Buje_{material.name}_{int(od)}x{int(id_val)}"

    return EspecificacionBuje(
        nombre_pieza=nombre,
        material=material,
        diametro_exterior_mm=od,
        diametro_interior_mm=id_val,
        longitud_mm=largo,
        chaflan_mm=chaflan,
        notas_mecanizado="Generado por motor local de respaldo (API Google saturada).",
    )


def interpretar_solicitud(prompt_usuario: str, forzar_local: bool = False) -> EspecificacionBuje:
    if forzar_local:
        print("[Modo Local] Usando parser determinista sin llamar a la nube.")
        return _parser_local_emergencia(prompt_usuario)

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Falta la variable GEMINI_API_KEY en el archivo .env.")

    client = genai.Client(api_key=api_key)
    
    for modelo in MODELOS_RESPALDO:
        try:
            response = client.models.generate_content(
                model=modelo,
                contents=prompt_usuario,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    response_schema=EspecificacionBuje,
                    temperature=0.1,
                ),
            )
            if response.parsed is not None:
                print(f"[IA] Respuesta generada con éxito usando: {modelo}")
                return response.parsed
        except Exception as e:
            print(f"[Aviso] {modelo} no respondió a tiempo ({type(e).__name__}).")
            continue

    print("[Respaldo Local] Nube saturada. Resolviendo instantáneamente con motor local.")
    return _parser_local_emergencia(prompt_usuario)