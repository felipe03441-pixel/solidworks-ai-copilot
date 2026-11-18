from enum import Enum
from pydantic import BaseModel, Field, model_validator


class MaterialMecanizado(str, Enum):
    BRONCE_SAE_660 = "Bronce SAE 660"
    ACERO_1045 = "Acero AISI 1045"
    ACERO_INOX_304 = "Acero Inoxidable 304"
    ALUMINIO_6061 = "Aluminio 6061-T6"
    NYLON_6 = "Nylon 6 (Poliamida)"


class EspecificacionBuje(BaseModel):
    nombre_pieza: str = Field(
        ...,
        description="Nombre técnico corto sin espacios, ej: Buje_Principal_Eje",
    )
    material: MaterialMecanizado = Field(
        default=MaterialMecanizado.BRONCE_SAE_660,
        description="Material seleccionado para el mecanizado",
    )
    diametro_exterior_mm: float = Field(
        ...,
        ge=5.0,
        le=500.0,
        description="Diámetro exterior (OD) en milímetros (entre 5 y 500 mm)",
    )
    diametro_interior_mm: float = Field(
        ...,
        ge=2.0,
        le=490.0,
        description="Diámetro interior o agujero pasante (ID) en milímetros (entre 2 y 490 mm)",
    )
    longitud_mm: float = Field(
        ...,
        ge=2.0,
        le=1000.0,
        description="Largo total del buje en milímetros (entre 2 y 1000 mm)",
    )
    chaflan_mm: float = Field(
        default=1.0,
        ge=0.0,
        le=10.0,
        description="Chaflán a 45 grados en ambos extremos en milímetros",
    )
    tolerancia_ajuste: str = Field(
        default="H7/g6",
        description="Ajuste ISO solicitado (ej. H7/g6, H7/p6, +/- 0.05 mm)",
    )
    notas_mecanizado: str = Field(
        default="",
        description="Observaciones adicionales para plano o torneado",
    )

    @property
    def espesor_pared_mm(self) -> float:
        return round((self.diametro_exterior_mm - self.diametro_interior_mm) / 2.0, 3)

    @model_validator(mode="after")
    def validar_geometria_mecanizable(self) -> "EspecificacionBuje":
        if self.diametro_interior_mm >= self.diametro_exterior_mm:
            raise ValueError(
                f"Geometría imposible: el diámetro interior ({self.diametro_interior_mm} mm) "
                f"debe ser menor que el exterior ({self.diametro_exterior_mm} mm)."
            )

        if self.espesor_pared_mm < 1.5:
            raise ValueError(
                f"Pared demasiado delgada ({self.espesor_pared_mm} mm): riesgo de deformación "
                "en el mandril del torno. El espesor mínimo de pared es 1.5 mm."
            )

        if self.chaflan_mm >= self.espesor_pared_mm:
            raise ValueError(
                f"El chaflán ({self.chaflan_mm} mm) consume todo el espesor de pared "
                f"({self.espesor_pared_mm} mm)."
            )

        return self