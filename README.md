# ⚙️ SolidWorks AI Parameter Copilot

Puente de automatización CAD que traduce especificaciones en lenguaje natural a parámetros geométricos validados para manufactura en torno, integrando **Google Gemini API (Structured Outputs)**, **Pydantic v2**, **Streamlit** y la **API COM de SolidWorks (`pywin32`)**.

## 🎯 Problema que resuelve
Automatizar la parametrización de componentes mecánicos cilíndricos (bujes, casquillos, camisas) evitando que lleguen al software CAD geometrías físicamente imposibles o riesgosas para el mecanizado en torno convencional o CNC.

## 🏗️ Arquitectura y Decisiones Técnicas

- **Contrato de Dominio (`src/domain/models.py`):** Validación estricta con `Pydantic`. Bloquea automáticamente:
  - Geometrías imposibles ($\emptyset_{int} \ge \emptyset_{ext}$).
  - Espesores de pared críticos ($e < 1.5\text{ mm}$) que provocan deformación por apriete en las mordazas del mandril.
  - Chaflanes que exceden el espesor de pared disponible.
- **Resiliencia y Tolerancia a Fallos (`src/domain/ai_parser.py`):** Estrategia *Multi-Model Fallback* ante errores `503/429` en la nube y motor determinista local (*Offline Regex Fallback*) para operación continua sin conexión.
- **Patrón Adaptador Dual (`src/adapters/cad_engine.py`):**
  - `SolidWorksCOMAdapter`: Conexión directa en Windows vía `SldWorks.Application` con conversión automática al Sistema Internacional (metros).
  - `MockCADAdapter`: Simulación desacoplada para pruebas unitarias, CI/CD y despliegue en la nube (Linux).

## 🚀 Instalación y Uso

1. Clonar el repositorio y crear el entorno virtual:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt