import streamlit as st
from pydantic import ValidationError
from src.domain.models import EspecificacionBuje
from src.domain.ai_parser import interpretar_solicitud
from src.adapters.cad_engine import MockCADAdapter, SolidWorksCOMAdapter

st.set_page_config(
    page_title="SolidWorks AI Copilot",
    page_icon="⚙️",
    layout="wide",
)

st.title("⚙️ SolidWorks AI Parameter Copilot")
st.caption(
    "Puente de automatización CAD: Traducción de lenguaje natural a parámetros validados de manufactura (Pydantic + Gemini API + SolidWorks COM)."
)

with st.sidebar:
    st.header("Configuración del Motor")
    modo_cad = st.radio(
        "Motor de Ejecución CAD:",
        options=["Simulación (Mock JSON / Cloud)", "SolidWorks Real (Windows COM)"],
        index=0,
    )
    forzar_local = st.checkbox(
        "Usar parser local ultrarrápido (Offline / Sin gastar cuota API)",
        value=True,
    )

col_izq, col_der = st.columns([1, 1])

with col_izq:
    st.subheader("1. Solicitud de Ingeniería")
    prompt_ejemplo = (
        "Necesito un buje en bronce SAE 660 de 50 mm exterior, "
        "25 mm interior, 60 mm de largo y chaflán de 1.5 mm"
    )
    prompt_usuario = st.text_area(
        "Describe la pieza o medidas requeridas (mm o pulgadas):",
        value=prompt_ejemplo,
        height=110,
    )

    if st.button("Interpretar y Validar Geometría", type="primary", use_container_width=True):
        try:
            with st.spinner("Analizando parámetros y reglas de torneado..."):
                spec = interpretar_solicitud(prompt_usuario, forzar_local=forzar_local)
                st.session_state["spec_actual"] = spec
                st.success("Geometría válida para mecanizado en torno.")
        except ValidationError as ve:
            st.session_state.pop("spec_actual", None)
            st.error("❌ Error de Validación de Manufactura (Bloqueo Preventivo):")
            for err in ve.errors():
                st.warning(err["msg"])
        except Exception as e:
            st.error(f"Error técnico: {e}")

with col_der:
    st.subheader("2. Verificación Técnica y Ejecución CAD")
    spec: EspecificacionBuje = st.session_state.get("spec_actual")

    if spec:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Ø Exterior (OD)", f"{spec.diametro_exterior_mm} mm")
        m2.metric("Ø Interior (ID)", f"{spec.diametro_interior_mm} mm")
        m3.metric("Espesor Pared", f"{spec.espesor_pared_mm} mm")
        m4.metric("Longitud", f"{spec.longitud_mm} mm")

        st.write(f"**Pieza:** `{spec.nombre_pieza}` | **Material:** `{spec.material.value}` | **Ajuste:** `{spec.tolerancia_ajuste}`")
        if spec.notas_mecanizado:
            st.info(f"Nota: {spec.notas_mecanizado}")

        with st.expander("Ver Contrato JSON validado (Pydantic Schema)", expanded=False):
            st.json(spec.model_dump())

        if st.button("🚀 Enviar a Motor CAD", use_container_width=True):
            try:
                adapter = MockCADAdapter() if "Simulación" in modo_cad else SolidWorksCOMAdapter()
                resultado = adapter.aplicar_especificacion(spec)
                st.success(resultado["mensaje"])
                st.write("**Variables inyectadas a la API de SolidWorks (en metros):**")
                st.json(resultado["parametros_api"])
            except Exception as e:
                st.error(f"Fallo al ejecutar en CAD: {e}")
    else:
        st.info("Haz clic en 'Interpretar y Validar Geometría' a la izquierda para previsualizar las cotas.")