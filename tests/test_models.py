import pytest
from pydantic import ValidationError
from src.domain.models import EspecificacionBuje, MaterialMecanizado


def test_buje_valido_calcula_espesor():
    buje = EspecificacionBuje(
        nombre_pieza="Buje_Test_50x25",
        material=MaterialMecanizado.BRONCE_SAE_660,
        diametro_exterior_mm=50.0,
        diametro_interior_mm=25.0,
        longitud_mm=60.0,
        chaflan_mm=1.5,
    )
    assert buje.espesor_pared_mm == 12.5


def test_bloquea_diametro_interior_mayor_que_exterior():
    with pytest.raises(ValidationError, match="Geometría imposible"):
        EspecificacionBuje(
            nombre_pieza="Buje_Invalido_ID",
            diametro_exterior_mm=30.0,
            diametro_interior_mm=35.0,
            longitud_mm=40.0,
        )


def test_bloquea_pared_delgada_riesgo_torno():
    with pytest.raises(ValidationError, match="Pared demasiado delgada"):
        EspecificacionBuje(
            nombre_pieza="Buje_Pared_Delgada",
            diametro_exterior_mm=20.0,
            diametro_interior_mm=18.0,  # Espesor = 1.0 mm (< 1.5 mm mínimo)
            longitud_mm=30.0,
            chaflan_mm=0.5,
        )


def test_bloquea_chaflan_excesivo():
    with pytest.raises(ValidationError, match="consume todo el espesor"):
        EspecificacionBuje(
            nombre_pieza="Buje_Chaflan_Grande",
            diametro_exterior_mm=20.0,
            diametro_interior_mm=15.0,  # Espesor = 2.5 mm
            longitud_mm=30.0,
            chaflan_mm=3.0,
        )