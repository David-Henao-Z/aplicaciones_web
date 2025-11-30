# Guía de Pruebas - API Bancaria

Pruebas básicas con pytest para validación de modelos Pydantic.

## 📁 Estructura

```
tests/
├── __init__.py           # Package marker
├── conftest.py           # Configuración básica
├── test_simple.py        # Pruebas de modelos Pydantic
└── README.md             # Este archivo
```

## 🧪 Pruebas Implementadas

### Modelos Pydantic (7 tests)
- ✅ `test_cliente_create_model`: Validación de ClienteCreate
- ✅ `test_deposito_payload_model`: Validación de Deposito
- ✅ `test_retiro_payload_model`: Validación de Retiro
- ✅ `test_transferencia_payload_model`: Validación de Transferencia
- ✅ `test_tipo_cuenta_enum`: Validación de enum TipoCuenta
- ✅ `test_cliente_nombre_minimo`: Validación de nombre mínimo
- ✅ `test_monto_positivo_deposito`: Validación de monto positivo

## 🚀 Instalación

```powershell
cd "c:\Users\Ardila\Desktop\U\Quinto Semestre\FastAPI\aplicaciones_web"
pip install -r requirements.txt
```

## ▶️ Ejecutar Pruebas

```powershell
# Todas las pruebas
python -m pytest tests/ -v

# Solo test_simple.py
python -m pytest tests/test_simple.py -v

# Con cobertura
python -m pytest --cov=aplicaciones_web.apis.functions tests/ -v
```

## 📊 Salida Esperada

```
tests/test_simple.py::test_cliente_create_model PASSED           [ 14%]
tests/test_simple.py::test_deposito_payload_model PASSED         [ 28%]
tests/test_simple.py::test_retiro_payload_model PASSED           [ 42%]
tests/test_simple.py::test_transferencia_payload_model PASSED    [ 57%]
tests/test_simple.py::test_tipo_cuenta_enum PASSED               [ 71%]
tests/test_simple.py::test_cliente_nombre_minimo PASSED          [ 85%]
tests/test_simple.py::test_monto_positivo_deposito PASSED        [100%]

========================= 7 passed in 0.5s =========================
```

## 📝 Descripción de Pruebas

### Pruebas de Creación de Modelos
Verifican que los modelos Pydantic se pueden crear con datos válidos:
- ClienteCreate: nombre y documento
- Deposito: cuenta y monto positivo
- Retiro: cuenta y monto positivo
- Transferencia: cuentas origen/destino y monto

### Pruebas de Validación
Verifican que las validaciones Pydantic funcionan correctamente:
- Nombre mínimo de 2 caracteres
- Montos deben ser positivos (PositiveFloat)

## 🎯 Alcance

Estas son **pruebas básicas de validación** que verifican:
- ✅ Estructura de modelos Pydantic
- ✅ Validaciones de campos
- ✅ Tipos de datos correctos

**No incluyen**:
- ❌ Pruebas de base de datos
- ❌ Pruebas de endpoints FastAPI
- ❌ Pruebas de lógica de negocio compleja

---

**Versión**: 1.0 (Simplificada)
