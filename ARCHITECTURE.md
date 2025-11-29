# Arquitectura del Sistema - Banco API

## Índice
1. [Visión General](#visión-general)
2. [Arquitectura de Capas](#arquitectura-de-capas)
3. [Estructura de Módulos](#estructura-de-módulos)
4. [Flujo de Datos](#flujo-de-datos)
5. [Seguridad](#seguridad)
6. [Base de Datos](#base-de-datos)
7. [Principios de Diseño](#principios-de-diseño)

---

## Visión General

Este proyecto implementa una **API REST** para un sistema bancario completo, desarrollado con **FastAPI** y **PostgreSQL**. La arquitectura sigue principios de **separación de responsabilidades** y **clean architecture** adaptados a microservicios.

### Stack Tecnológico

| Componente | Tecnología | Versión | Propósito |
|------------|------------|---------|-----------|
| Framework Web | FastAPI | 0.115+ | Endpoints REST y documentación automática |
| Servidor ASGI | Uvicorn | Latest | Servidor HTTP asíncrono de alto rendimiento |
| Validación | Pydantic | 2.x | Validación de datos y serialización |
| Base de Datos | PostgreSQL | Latest | Almacenamiento persistente (Neon) |
| Driver DB | asyncpg | Latest | Cliente PostgreSQL asíncrono |
| Autenticación | python-jose | Latest | JWT token generation/validation |
| Hashing | bcrypt | 4.1.3 | Encriptación de contraseñas |
| Variables Entorno | python-dotenv | Latest | Gestión de configuración |

---

## Arquitectura de Capas

El proyecto está organizado en **4 capas principales**, siguiendo el patrón de arquitectura hexagonal adaptado:

```
┌─────────────────────────────────────────┐
│         Presentation Layer              │
│    (crud.py - FastAPI Endpoints)        │
│  - Validación de entrada HTTP           │
│  - Serialización de respuestas          │
│  - Manejo de autenticación              │
│  - Documentación OpenAPI                │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│         Business Logic Layer            │
│    (functions.py - Services)            │
│  - Reglas de negocio                    │
│  - Validaciones complejas               │
│  - Orquestación de operaciones          │
│  - Transformación de datos              │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│         Data Access Layer               │
│    (database.py - Repository)           │
│  - Connection pooling                   │
│  - Consultas SQL                        │
│  - Manejo de transacciones              │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│         Infrastructure Layer            │
│    (PostgreSQL + Neon)                  │
│  - Almacenamiento persistente           │
│  - Índices y constraints                │
│  - Triggers y procedimientos            │
└─────────────────────────────────────────┘
```

### Capa Transversal: Seguridad

```
┌─────────────────────────────────────────┐
│         Security Layer                  │
│    (auth.py - Authentication)           │
│  - Generación de JWT                    │
│  - Validación de tokens                 │
│  - Hashing de contraseñas               │
│  - OAuth2 flow                          │
└─────────────────────────────────────────┘
```

---

## Estructura de Módulos

### 1. `crud.py` - Capa de Presentación

**Responsabilidades:**
- Definir endpoints REST (GET, POST, PUT, DELETE)
- Validar entrada HTTP con Pydantic
- Manejar autenticación JWT con decoradores
- Generar documentación OpenAPI automática
- Transformar excepciones a respuestas HTTP

**Patrón de diseño:** Controller Pattern

```python
# Ejemplo de estructura de endpoint
@app.post("/clientes", response_model=Cliente, status_code=201)
async def crear_cliente(
    payload: ClienteCreate,  # Validación automática
    current_user: User = Depends(get_current_user)  # Autenticación
):
    """Crea un nuevo cliente - Requiere autenticación JWT"""
    try:
        return await svc.crear_cliente(payload)  # Delegación a capa de negocio
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

---

### 2. `functions.py` - Capa de Lógica de Negocio

**Responsabilidades:**
- Implementar reglas de negocio complejas
- Validar restricciones del dominio
- Coordinar operaciones multi-tabla
- Transformar datos entre capas
- Definir modelos Pydantic

**Patrón de diseño:** Service Layer Pattern

**Reglas de negocio implementadas:**

#### Clientes
- ✅ Documento único por cliente
- ✅ No se puede eliminar cliente con cuentas activas
- ✅ Nombre completo mínimo 2 caracteres

#### Cuentas
- ✅ Número de cuenta autogenerado único
- ✅ Saldo nunca negativo
- ✅ Solo se elimina si saldo = 0
- ✅ Asociación obligatoria a cliente y tipo

#### Transacciones
- ✅ **Depósito:** solo cuenta destino
- ✅ **Retiro:** validar fondos suficientes
- ✅ **Transferencia:** origen ≠ destino, validar fondos
- ✅ Montos siempre positivos
- ✅ Actualización automática de saldos

---

### 3. `database.py` - Capa de Acceso a Datos

**Responsabilidades:**
- Gestionar pool de conexiones PostgreSQL
- Proporcionar context manager para transacciones
- Manejar lifecycle de conexiones
- Configurar timeouts y límites

**Patrón de diseño:** Repository Pattern + Connection Pool

```python
# Pool de conexiones con asyncpg
async def get_pool():
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=1,    # Mínimo de conexiones
            max_size=10    # Máximo de conexiones concurrentes
        )
    return _pool

# Context manager para transacciones automáticas
@asynccontextmanager
async def get_db():
    pool = await get_pool()
    async with pool.acquire() as connection:
        yield connection  # Libera automáticamente al salir
```

---

### 4. `auth.py` - Capa de Seguridad

**Responsabilidades:**
- Autenticación de usuarios
- Generación de tokens JWT
- Validación de tokens
- Hashing de contraseñas con bcrypt
- Gestión de sesiones

**Estándar:** OAuth2 + JWT (RFC 7519)

```python
# Flujo de autenticación
1. Usuario envía credenciales → POST /token
2. Sistema valida contra BD (bcrypt.verify)
3. Si válido → genera JWT firmado (HMAC-SHA256)
4. Cliente almacena token → localStorage/sessionStorage
5. Cada request incluye: Authorization: Bearer <token>
6. FastAPI valida token en cada endpoint protegido
```

**Configuración de seguridad:**
- Algoritmo: HS256 (HMAC con SHA-256)
- Expiración: 60 minutos
- Secret Key: Configurable por variable de entorno
- Password hashing: bcrypt con 12 rounds

---

## Flujo de Datos

### Ejemplo: Crear Cliente

```
1. Cliente HTTP                  │  POST /clientes
   └─> Headers: Authorization    │  Body: {nombre, documento}
                                  │
2. FastAPI Middleware             │  
   └─> Valida JWT                 │  get_current_user()
   └─> Extrae user del token      │
                                  │
3. crud.py                        │  crear_cliente()
   └─> Valida schema Pydantic     │  ClienteCreate
   └─> try/catch para errores     │
                                  │
4. functions.py                   │  svc.crear_cliente()
   └─> Verifica documento único   │  SELECT EXISTS...
   └─> Inserta en BD              │  INSERT INTO...
   └─> Retorna Cliente            │
                                  │
5. database.py                    │  get_db()
   └─> Pool de conexiones         │  asyncpg.pool
   └─> Execute query              │  conn.fetchrow()
   └─> Auto-commit                │
                                  │
6. FastAPI Response               │  HTTP 201 Created
   └─> Serializa a JSON           │  {id, nombre, documento, ...}
   └─> Headers CORS               │  Access-Control-*
```

---

## Seguridad

### Autenticación JWT

**Flujo completo:**

```
┌──────────┐                    ┌──────────┐
│  Client  │                    │  Server  │
└────┬─────┘                    └────┬─────┘
     │                               │
     │  POST /token                  │
     │  username + password          │
     ├──────────────────────────────>│
     │                               │
     │                          [Valida credenciales]
     │                          [Genera JWT]
     │                               │
     │  200 OK                       │
     │  {access_token, token_type}   │
     │<──────────────────────────────┤
     │                               │
     │  GET /clientes                │
     │  Authorization: Bearer <JWT>  │
     ├──────────────────────────────>│
     │                               │
     │                          [Valida firma JWT]
     │                          [Verifica expiración]
     │                          [Extrae usuario]
     │                          [Ejecuta endpoint]
     │                               │
     │  200 OK                       │
     │  [Lista de clientes]          │
     │<──────────────────────────────┤
```

### Estructura del JWT

```json
{
  "header": {
    "alg": "HS256",
    "typ": "JWT"
  },
  "payload": {
    "sub": "admin@banco.com",
    "exp": 1735516800
  },
  "signature": "HMACSHA256(base64(header).base64(payload), SECRET_KEY)"
}
```

### Endpoints Públicos vs Protegidos

| Endpoint | Método | Autenticación | Propósito |
|----------|--------|---------------|-----------|
| `/` | GET | ❌ No | Healthcheck |
| `/token` | POST | ❌ No | Login (generar JWT) |
| `/docs` | GET | ❌ No | Documentación Swagger |
| `/clientes` | GET/POST | ✅ Sí | Gestión de clientes |
| `/cuentas` | GET/POST/DELETE | ✅ Sí | Gestión de cuentas |
| `/transacciones/*` | GET/POST/DELETE | ✅ Sí | Operaciones bancarias |

---

## Base de Datos

### Esquema Lógico

```sql
-- Schema: banco
CREATE SCHEMA banco;

-- Tabla: cliente
CREATE TABLE banco.cliente (
    id_cliente UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre_completo VARCHAR(255) NOT NULL,
    documento VARCHAR(50) UNIQUE NOT NULL,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_edicion TIMESTAMP
);

-- Tabla: tipo_cuenta
CREATE TABLE banco.tipo_cuenta (
    id_tipo_cuenta UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre VARCHAR(50) UNIQUE NOT NULL,  -- AHORROS, CORRIENTE
    descripcion TEXT
);

-- Tabla: cuenta
CREATE TABLE banco.cuenta (
    id_cuenta UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    numero VARCHAR(20) UNIQUE NOT NULL,
    id_cliente UUID REFERENCES banco.cliente(id_cliente),
    id_tipo_cuenta UUID REFERENCES banco.tipo_cuenta(id_tipo_cuenta),
    saldo NUMERIC(15,2) DEFAULT 0 CHECK (saldo >= 0),
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_edicion TIMESTAMP
);

-- Tabla: transaccion
CREATE TABLE banco.transaccion (
    id_transaccion UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tipo VARCHAR(50) NOT NULL,  -- DEPOSITO, RETIRO, TRANSFERENCIA
    id_cuenta_origen UUID REFERENCES banco.cuenta(id_cuenta),
    id_cuenta_destino UUID REFERENCES banco.cuenta(id_cuenta),
    monto NUMERIC(15,2) NOT NULL CHECK (monto > 0),
    momento TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_edicion TIMESTAMP
);

-- Índices para optimización
CREATE INDEX idx_cliente_documento ON banco.cliente(documento);
CREATE INDEX idx_cuenta_cliente ON banco.cuenta(id_cliente);
CREATE INDEX idx_transaccion_origen ON banco.transaccion(id_cuenta_origen);
CREATE INDEX idx_transaccion_destino ON banco.transaccion(id_cuenta_destino);
CREATE INDEX idx_transaccion_momento ON banco.transaccion(momento DESC);
```

### Relaciones

```
cliente (1) ──────< (N) cuenta
                      │
                      │ (1)
                      │
                      ▼ (N)
                  transaccion
```

**Cardinalidades:**
- Un cliente puede tener múltiples cuentas (1:N)
- Una cuenta pertenece a un solo cliente (N:1)
- Una transacción involucra 1 o 2 cuentas según el tipo

---

## Principios de Diseño

### 1. **Separation of Concerns (SoC)**
- Cada módulo tiene una responsabilidad única y bien definida
- Bajo acoplamiento entre capas
- Alta cohesión dentro de cada capa

### 2. **Dependency Inversion Principle (DIP)**
- Las capas superiores no dependen de implementaciones específicas
- Uso de abstracciones (interfaces de Pydantic)
- Inyección de dependencias con FastAPI Depends()

### 3. **Single Responsibility Principle (SRP)**
- Cada función tiene un propósito único
- Módulos pequeños y enfocados
- Fácil de testear unitariamente

### 4. **Don't Repeat Yourself (DRY)**
- Lógica de negocio centralizada en `functions.py`
- Modelos Pydantic reutilizables
- Pool de conexiones compartido

### 5. **Fail Fast**
- Validación temprana con Pydantic
- Excepciones específicas por capa
- Logging de errores críticos

### 6. **Explicit is Better Than Implicit**
- Type hints en todas las funciones
- Nombres descriptivos de variables
- Documentación exhaustiva (docstrings)

---

## Patrones de Diseño Aplicados

| Patrón | Ubicación | Propósito |
|--------|-----------|-----------|
| **Repository** | `database.py` | Abstracción de acceso a datos |
| **Service Layer** | `functions.py` | Lógica de negocio centralizada |
| **Dependency Injection** | `crud.py` (`Depends()`) | Desacoplamiento de componentes |
| **Singleton** | `database.py` (pool) | Única instancia de pool de conexiones |
| **Factory** | `_generar_numero_cuenta()` | Creación de números únicos |
| **Context Manager** | `get_db()` | Gestión automática de recursos |

---

## Mejores Prácticas Implementadas

✅ **Async/Await** - Operaciones I/O no bloqueantes  
✅ **Type Hints** - Tipado estático para mejor IDE support  
✅ **Pydantic Models** - Validación automática de datos  
✅ **Connection Pooling** - Reutilización eficiente de conexiones  
✅ **Environment Variables** - Configuración externa segura  
✅ **CORS Middleware** - Seguridad para integraciones frontend  
✅ **Auto-documentation** - Swagger UI y ReDoc  
✅ **Error Handling** - Excepciones específicas por caso  
✅ **Password Hashing** - bcrypt para seguridad de contraseñas  
✅ **JWT Stateless** - Escalabilidad sin sesiones en servidor  

---

## Escalabilidad y Performance

### Optimizaciones Actuales

1. **Connection Pooling** - Hasta 10 conexiones concurrentes
2. **Async Operations** - No bloquea el event loop
3. **Índices de BD** - Consultas optimizadas
4. **Pydantic Caching** - Validación rápida de schemas

### Futuras Mejoras

- [ ] Redis para caché de consultas frecuentes
- [ ] Rate limiting por usuario
- [ ] Paginación en listados grandes
- [ ] Compresión de respuestas HTTP (gzip)
- [ ] Load balancer para múltiples instancias

---

**Última actualización:** 29 de noviembre de 2025  
**Versión del documento:** 1.0  
**Autores:** David Henao Zea, HOLOMAN582, Santiago Ardila
