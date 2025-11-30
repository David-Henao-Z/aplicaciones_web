# test_simple.py
"""
Pruebas básicas para modelos Pydantic de la API Bancaria.
"""

import pytest
from uuid import UUID
from datetime import datetime

from aplicaciones_web.apis.functions import (
    ClienteCreate,
    Deposito,
    Retiro,
    Transferencia,
    TipoCuenta,
)


# ============================================================================
# Tests: Modelos Pydantic - Casos Exitosos
# ============================================================================

@pytest.mark.unit
def test_cliente_create_model():
    """Prueba creación de modelo ClienteCreate."""
    # Arrange & Act
    cliente_create = ClienteCreate(
        nombre_completo="María García",
        documento="87654321"
    )
    
    # Assert
    assert cliente_create.nombre_completo == "María García"
    assert cliente_create.documento == "87654321"


@pytest.mark.unit
def test_deposito_payload_model():
    """Prueba creación de modelo Deposito (payload)."""
    # Arrange & Act
    deposito = Deposito(
        id_cuenta=UUID("789e0123-b45c-67d8-e901-234567890abc"),
        monto=100.0
    )
    
    # Assert
    assert deposito.monto == 100.0
    assert deposito.monto > 0


@pytest.mark.unit
def test_retiro_payload_model():
    """Prueba creación de modelo Retiro (payload)."""
    # Arrange & Act
    retiro = Retiro(
        id_cuenta=UUID("789e0123-b45c-67d8-e901-234567890abc"),
        monto=50.0
    )
    
    # Assert
    assert retiro.monto == 50.0
    assert retiro.monto > 0


@pytest.mark.unit
def test_transferencia_payload_model():
    """Prueba creación de modelo Transferencia (payload)."""
    # Arrange & Act
    transferencia = Transferencia(
        id_cuenta_origen=UUID("789e0123-b45c-67d8-e901-234567890abc"),
        id_cuenta_destino=UUID("abc0123d-e45f-6789-0123-456789abcdef"),
        monto=25.0
    )
    
    # Assert
    assert transferencia.monto == 25.0
    assert transferencia.id_cuenta_origen != transferencia.id_cuenta_destino


@pytest.mark.unit
def test_tipo_cuenta_enum():
    """Prueba constantes de TipoCuenta."""
    # Assert
    assert TipoCuenta.AHORROS == "AHORROS"
    assert TipoCuenta.CORRIENTE == "CORRIENTE"


# ============================================================================
# Tests: Validaciones Pydantic
# ============================================================================

@pytest.mark.unit
def test_cliente_nombre_minimo():
    """Prueba validación de nombre mínimo en Cliente."""
    # Act & Assert
    with pytest.raises(Exception):  # Pydantic ValidationError
        ClienteCreate(nombre_completo="A", documento="123")


@pytest.mark.unit
def test_monto_positivo_deposito():
    """Prueba validación de monto positivo en Deposito."""
    # Act & Assert
    with pytest.raises(Exception):  # Pydantic ValidationError
        Deposito(
            id_cuenta=UUID("789e0123-b45c-67d8-e901-234567890abc"),
            monto=-100.0
        )
