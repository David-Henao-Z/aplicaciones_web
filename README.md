# Banco API (FastAPI) — Modular

API educativa que modela un **Banco** con tres recursos principales: **Clientes**, **Cuentas** y **Transacciones**.  
Incluye CRUD completo, validaciones, parámetros de ruta y consulta, y documentación interactiva (Swagger/ReDoc).  
La “base de datos” es **en memoria** (se pierde al reiniciar).

## Características

- **Clientes**: crear, listar, obtener por ID, actualizar, eliminar (con regla: no borrar si tiene cuentas).
- **Cuentas**: crear (num. autogenerado `ACC0001…`), listar (filtros por cliente y tipo), obtener, actualizar tipo, eliminar (regla: saldo = 0).
- **Transacciones**: listar (filtros por cuenta y fechas), **CRUD por id** (obtener/actualizar/eliminar) y operaciones de **depósito**, **retiro** y **transferencia** con validaciones de negocio (fondos suficientes, origen≠destino).
- **Autodocumentación**: Swagger UI y ReDoc.

## Requisitos

- **Python 3.10+**
- **pip**
- (Opcional) Postman o la extensión **Thunder Client** en VS Code

## Instalación

En la carpeta raíz del proyecto (donde están `crud.py` y `functions.py`):

**Windows (PowerShell)**

```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install "fastapi" "uvicorn[standard]" "pydantic[email]"
```

**Linux / macOS**

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install "fastapi" "uvicorn[standard]" "pydantic[email]"
```

> Si usas `EmailStr` (lo usamos en Cliente), **pydantic[email]** instala el validador de emails requerido.

## Ejecución

Desde la raíz del proyecto:

```bash
python -m uvicorn crud:app --reload
```

- Base URL: `http://127.0.0.1:8000`
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

## Estructura

```text
.
├── crud.py         # Endpoints FastAPI (controladores)
├── functions.py    # Modelos y lógica/reglas de negocio (servicios)
└── README.md
```

## Endpoints

### Salud

| Método | Ruta | Descripción |
| ------ | ---- | ----------- |
| GET    | `/`  | Healthcheck |

### Clientes

| Método | Ruta                     | Descripción                            |
| ------ | ------------------------ | -------------------------------------- |
| GET    | `/clientes`              | Listar clientes                        |
| GET    | `/clientes/{cliente_id}` | Obtener cliente por ID                 |
| POST   | `/clientes`              | Crear cliente (email único)            |
| PUT    | `/clientes/{cliente_id}` | Actualizar cliente                     |
| DELETE | `/clientes/{cliente_id}` | Eliminar cliente (si no tiene cuentas) |

**Ejemplo POST /clientes**

```json
{ "nombre": "David Jiménez", "email": "david@example.com" }
```

### Cuentas

| Método | Ruta                | Descripción                                  |
| ------ | ------------------- | -------------------------------------------- | --------- | --------- |
| GET    | `/cuentas`          | Listar cuentas (query: `cliente_id`, `tipo`) |
| GET    | `/cuentas/{numero}` | Obtener cuenta por número                    |
| POST   | `/cuentas`          | Crear cuenta (número autogenerado)           |
| PUT    | `/cuentas/{numero}` | Actualizar **tipo** (query: `tipo=AHORROS    | CORRIENTE | CREDITO`) |
| DELETE | `/cuentas/{numero}` | Eliminar cuenta (requiere saldo = 0)         |

**Ejemplo POST /cuentas**

```json
{ "cliente_id": 1, "tipo": "AHORROS" }
```

**Ejemplo PUT /cuentas/{numero}**

```
/cuentas/ACC0001?tipo=CORRIENTE
```

### Transacciones

| Método | Ruta                           | Descripción                                               |
| ------ | ------------------------------ | --------------------------------------------------------- |
| GET    | `/transacciones`               | Listar (query: `cuenta`, `desde`, `hasta` — `YYYY-MM-DD`) |
| GET    | `/transacciones/{tx_id}`       | Obtener transacción por ID                                |
| PUT    | `/transacciones/{tx_id}`       | Actualizar transacción (campo `nota`)                     |
| DELETE | `/transacciones/{tx_id}`       | Eliminar transacción                                      |
| POST   | `/transacciones/deposito`      | Depositar en cuenta                                       |
| POST   | `/transacciones/retiro`        | Retirar de cuenta                                         |
| POST   | `/transacciones/transferencia` | Transferir entre cuentas                                  |

**Cuerpos de ejemplo**

- Depósito

```json
{ "cuenta": "ACC0001", "monto": 100000 }
```

- Retiro

```json
{ "cuenta": "ACC0001", "monto": 25000 }
```

- Transferencia

```json
{ "origen": "ACC0001", "destino": "ACC0002", "monto": 30000 }
```

**Actualización de transacción (PUT /transacciones/{tx_id})**

```json
{ "nota": "Ajuste por reversión manual" }
```

**Consulta con filtros**

```
GET /transacciones?cuenta=ACC0001&desde=2025-08-01&hasta=2025-08-31
```

## Ejemplos rápidos (cURL)

```bash
# Crear cliente
curl -X POST "http://127.0.0.1:8000/clientes" \
  -H "Content-Type: application/json" \
  -d '{"nombre":"David Jiménez","email":"david@example.com"}'

# Crear cuenta para cliente 1
curl -X POST "http://127.0.0.1:8000/cuentas" \
  -H "Content-Type: application/json" \
  -d '{"cliente_id":1,"tipo":"AHORROS"}'

# Depósito
curl -X POST "http://127.0.0.1:8000/transacciones/deposito" \
  -H "Content-Type: application/json" \
  -d '{"cuenta":"ACC0001","monto":100000}'

# Listar transacciones por cuenta
curl "http://127.0.0.1:8000/transacciones?cuenta=ACC0001"
```

## Autores / Integrantes

- **HOLOMAN582** — Estudiante / Desarrollador
- **Integrante 2** — Rol
- **Integrante 3** — Rol

> Reemplaza los nombres/roles según tu equipo.

## 🔮 Mejoras sugeridas

- Persistencia real con **SQLite/PostgreSQL** (SQLModel/SQLAlchemy).
- Autenticación (por ejemplo **JWT**) y control de acceso.
- Tests automatizados (pytest) y CI.
- Manejo de excepciones/global error handler y logs estructurados.
