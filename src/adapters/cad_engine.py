import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
from src.domain.models import EspecificacionBuje


class MockCADAdapter:
    """
    Motor de simulación para pruebas locales sin SolidWorks abierto,
    CI/CD en GitHub Actions y despliegue en Streamlit Cloud (Linux).
    """

    def aplicar_especificacion(self, spec: EspecificacionBuje) -> Dict[str, Any]:
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archivo_json = output_dir / f"{spec.nombre_pieza}_{timestamp}.json"

        payload_cad = {
            "modo_ejecucion": "SIMULACION_MOCK",
            "timestamp": timestamp,
            "pieza": spec.model_dump(),
            "espesor_pared_calculado_mm": spec.espesor_pared_mm,
            "variables_api_solidworks_metros": {
                "D1@Croquis1 (OD_m)": round(spec.diametro_exterior_mm / 1000.0, 6),
                "D2@Croquis1 (ID_m)": round(spec.diametro_interior_mm / 1000.0, 6),
                "D1@Saliente-Extruir1 (Largo_m)": round(spec.longitud_mm / 1000.0, 6),
                "D1@Chaflán1 (Chaflan_m)": round(spec.chaflan_mm / 1000.0, 6),
            },
            "propiedades_personalizadas": {
                "Material": spec.material.value,
                "Tolerancia": spec.tolerancia_ajuste,
                "Notas": spec.notas_mecanizado,
            },
        }

        archivo_json.write_text(
            json.dumps(payload_cad, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        return {
            "exito": True,
            "modo": "Simulación (Sin SolidWorks)",
            "mensaje": f"Especificación validada y exportada en {archivo_json}",
            "ruta_archivo": str(archivo_json),
            "parametros_api": payload_cad["variables_api_solidworks_metros"],
        }


class SolidWorksCOMAdapter:
    """
    Conector real con SolidWorks 2025 en Windows mediante automatización COM (pywin32).
    Soporta árboles de operaciones en Español (Croquis1) e Inglés (Sketch1).
    """

    def __init__(self, ruta_plantilla: str = "templates/buje_base.SLDPRT"):
        self.ruta_plantilla = str(Path(ruta_plantilla).resolve())

    def _asignar_cota_bilingue(
        self, model: Any, candidatos: list[str], valor_metros: float
    ) -> str:
        for nombre_cota in candidatos:
            try:
                param = model.Parameter(nombre_cota)
            except Exception:
                param = None
            if param is not None:
                param.SystemValue = valor_metros
                return nombre_cota
        raise RuntimeError(
            f"No se encontró ninguna de las cotas esperadas {candidatos} en la pieza. "
            "Verifica que la pieza abierta en SolidWorks sea buje_base.SLDPRT."
        )

    def aplicar_especificacion(self, spec: EspecificacionBuje) -> Dict[str, Any]:
        try:
            import pythoncom
            import win32com.client
        except ImportError:
            raise RuntimeError(
                "pywin32 no está disponible. Ejecuta en Windows o usa MockCADAdapter."
            )

        pythoncom.CoInitialize()

        try:
            sw_app = win32com.client.Dispatch("SldWorks.Application")
            sw_app.Visible = True
        except Exception as e:
            raise RuntimeError(f"No se pudo conectar con SolidWorks 2025 via COM: {e}")

        # 1. Tomar el documento activo si ya está abierto en SolidWorks
        model = sw_app.ActiveDoc

        # 2. Si no hay documento abierto, intentar abrir la plantilla desde disco
        if model is None:
            if not os.path.exists(self.ruta_plantilla):
                raise FileNotFoundError(
                    f"No hay ninguna pieza abierta en SolidWorks ni existe la plantilla en: {self.ruta_plantilla}."
                )
            model = sw_app.OpenDoc(self.ruta_plantilla, 1)

        if model is None:
            raise RuntimeError(
                "No se pudo acceder a la pieza en SolidWorks. Abre templates/buje_base.SLDPRT."
            )

        # Conversión obligatoria a metros (SI interno de la API de SolidWorks)
        mapa_candidatos = {
            "OD (Exterior)": (
                ["OD@Croquis1", "D1@Croquis1", "OD@Sketch1", "D1@Sketch1"],
                spec.diametro_exterior_mm / 1000.0,
            ),
            "ID (Interior)": (
                ["ID@Croquis1", "D2@Croquis1", "ID@Sketch1", "D2@Sketch1"],
                spec.diametro_interior_mm / 1000.0,
            ),
            "Longitud": (
                ["D1@Saliente-Extruir1", "Largo@Saliente-Extruir1", "D1@Boss-Extrude1"],
                spec.longitud_mm / 1000.0,
            ),
            "Chaflán": (
                ["D1@Chaflán1", "D1@Chaflan1", "D1@Chamfer1"],
                spec.chaflan_mm / 1000.0,
            ),
        }

        cotas_actualizadas = {}
        for etiqueta, (candidatos, valor_m) in mapa_candidatos.items():
            cota_encontrada = self._asignar_cota_bilingue(model, candidatos, valor_m)
            cotas_actualizadas[f"{etiqueta} -> {cota_encontrada}"] = round(valor_m, 6)

        # Forzar reconstrucción 3D (Ctrl + Q) y ajustar zoom en SolidWorks 2025
        _ = model.EditRebuild3
        try:
            model.ForceRebuild3(False)
        except TypeError:
            _ = model.ForceRebuild3
        _ = model.ViewZoomtofit2

        # Guardar pieza resultante en output/
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        ruta_salida = str((output_dir / f"{spec.nombre_pieza}.SLDPRT").resolve())

        try:
            model.SaveAs(ruta_salida)
        except Exception:
            pass

        return {
            "exito": True,
            "modo": "SolidWorks 2025 COM Real (Español)",
            "mensaje": f"Pieza 3D regenerada en vivo en SolidWorks 2025 y guardada en: {ruta_salida}",
            "ruta_archivo": ruta_salida,
            "parametros_api": cotas_actualizadas,
        }