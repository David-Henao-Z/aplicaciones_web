"""
database.py - Módulo de Gestión de Base de Datos
================================================

Este módulo maneja todas las conexiones y operaciones con PostgreSQL
utilizando asyncpg para operaciones asíncronas de alto rendimiento.

Funcionalidades principales:
    - Connection pooling para reutilización eficiente de conexiones
    - Context managers para manejo automático de transacciones
    - Configuración desde variables de entorno (.env)
    - Lifecycle management (startup/shutdown)

Arquitectura:
    - Pool Global: Una única instancia de pool compartida por toda la app
    - Async I/O: Operaciones no bloqueantes con asyncio
    - Auto-commit: Las transacciones se confirman automáticamente

Configuración:
    DATABASE_URL (env): Connection string de PostgreSQL
        Formato: postgresql://usuario:password@host:puerto/database
        Ejemplo Neon: postgresql://user:pass@ep-xxx.neon.tech/banco?sslmode=require

Performance:
    - min_size=1: Mantiene al menos 1 conexión siempre abierta
    - max_size=10: Hasta 10 conexiones concurrentes máximo
    - asyncpg: ~3x más rápido que psycopg2

Example:
    >>> # Usar el context manager en una función
    >>> async def get_clientes():
    ...     async with get_db() as conn:
    ...         rows = await conn.fetch("SELECT * FROM cliente")
    ...         return rows

Security:
    - Prepared statements automáticos (previene SQL injection)
    - Passwords nunca se loguean
    - SSL mode configurable vía connection string

Author: David Henao Zea, HOLOMAN582
Version: 2.0.0
Last Updated: 2025-11-29
"""

# database.py
# ============================================================================
# Configuración y conexión a la base de datos PostgreSQL
# ============================================================================

# ============================================================================
# Importaciones
# ============================================================================
import os
from dotenv import load_dotenv  # Carga variables de entorno desde .env
import asyncpg  # Driver PostgreSQL asíncrono
from contextlib import asynccontextmanager  # Para context managers

# ============================================================================
# Configuración de Base de Datos
# ============================================================================

# Cargar variables de entorno desde archivo .env
# Busca .env en el directorio actual y superiores
load_dotenv()

# Obtener connection string desde variable de entorno
# Formato: postgresql://usuario:password@host:puerto/database?opciones
# Ejemplo local: postgresql://postgres:admin@localhost:5432/banco
# Ejemplo Neon: postgresql://user:pass@ep-xxx.neon.tech/banco?sslmode=require
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/testdb")

# Validar configuración y mostrar advertencia si usa valores por defecto
if not DATABASE_URL or DATABASE_URL == "postgresql://user:pass@localhost/testdb":
    print("⚠️  Usando configuración de base de datos temporal - Solo para testing")
    print("    Para producción, configura DATABASE_URL en archivo .env")
    print("    Ejemplo: DATABASE_URL=postgresql://user:pass@host/dbname")

# ============================================================================
# Connection Pool Global
# ============================================================================
# Patrón Singleton: Una única instancia de pool compartida por toda la aplicación
# Se inicializa en el primer uso y se reutiliza en requests subsecuentes

_pool: asyncpg.Pool | None = None  # Pool global (inicialmente None)


async def get_pool() -> asyncpg.Pool:
    """
    Obtiene o crea el pool de conexiones a PostgreSQL.
    
    Implementa el patrón Singleton para asegurar que solo exista
    una instancia del pool de conexiones en toda la aplicación.
    
    Returns:
        asyncpg.Pool: Pool de conexiones configurado y listo para usar
    
    Connection Pool Configuration:
        - min_size=1: Mantiene al menos 1 conexión siempre abierta
        - max_size=10: Permite hasta 10 conexiones concurrentes
        - Auto-reconnect: Reconecta automáticamente si se pierde conexión
        - Prepared statements: Cache automático de queries frecuentes
    
    Performance Benefits:
        - Evita overhead de crear/cerrar conexiones
        - Reutiliza conexiones existentes
        - Múltiples requests pueden usar el pool simultáneamente
        - asyncpg es ~3x más rápido que psycopg2
    
    Example:
        >>> pool = await get_pool()
        >>> async with pool.acquire() as conn:
        ...     result = await conn.fetchval("SELECT COUNT(*) FROM cliente")
        ...     print(f"Total clientes: {result}")
    
    Note:
        - Esta función es llamada automáticamente por get_db()
        - No es necesario llamarla directamente en la mayoría de casos
        - El pool se cierra automáticamente con close_pool() en shutdown
    
    Raises:
        asyncpg.PostgresError: Si no se puede conectar a la base de datos
        asyncpg.InvalidCatalogNameError: Si la base de datos no existe
    """
    global _pool
    if _pool is None:
        # Crear pool con configuración optimizada
        _pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=1,    # Mínimo de conexiones mantenidas abiertas
            max_size=10,   # Máximo de conexiones simultáneas
            # Opciones adicionales disponibles:
            # timeout=30,           # Timeout en segundos
            # command_timeout=60,   # Timeout por comando
            # max_queries=50000,    # Máx queries antes de recrear conexión
            # max_inactive_connection_lifetime=300,  # 5 minutos de inactividad
        )
    return _pool


async def close_pool() -> None:
    """
    Cierra el pool de conexiones y libera todos los recursos.
    
    Esta función debe llamarse durante el shutdown de la aplicación
    para cerrar ordenadamente todas las conexiones a la base de datos.
    
    Lifecycle:
        - Startup: El pool se crea automáticamente en el primer uso
        - Runtime: El pool permanece activo y reutiliza conexiones
        - Shutdown: close_pool() cierra todas las conexiones y libera recursos
    
    What it does:
        1. Cierra todas las conexiones activas en el pool
        2. Cancela cualquier operación pendiente
        3. Libera memoria y recursos del sistema
        4. Resetea el pool global a None
    
    Example:
        >>> # En el lifespan de FastAPI
        >>> @asynccontextmanager
        >>> async def lifespan(app: FastAPI):
        ...     # Startup
        ...     yield
        ...     # Shutdown
        ...     await close_pool()  # Cierra conexiones al apagar
    
    Note:
        - Esta función es llamada automáticamente por FastAPI en shutdown
        - No es necesario llamarla manualmente en endpoints
        - Es seguro llamarla múltiples veces (idempotente)
        - Es una operación asíncrona (await required)
    
    Graceful Shutdown:
        - Espera a que terminen las operaciones en curso
        - No acepta nuevas conexiones durante el cierre
        - Previene memory leaks en reinicios de servidor
    """
    global _pool
    if _pool:
        # Cerrar todas las conexiones del pool
        await _pool.close()
        # Resetear la variable global
        _pool = None


@asynccontextmanager
async def get_db():
    """
    Context manager para obtener una conexión de base de datos.
    
    Este es el punto de entrada principal para todas las operaciones de BD.
    Proporciona una conexión del pool y la libera automáticamente al salir.
    
    Yields:
        asyncpg.Connection: Conexión activa lista para ejecutar queries
    
    Context Manager Benefits:
        - Automatic resource management (RAII pattern)
        - Libera la conexión automáticamente (incluso si hay excepciones)
        - Transacciones implícitas (auto-commit por defecto)
        - Previene connection leaks
    
    Usage Pattern:
        >>> async with get_db() as conn:
        ...     # La conexión está activa aquí
        ...     result = await conn.fetch("SELECT * FROM cliente")
        ...     # La conexión se libera automáticamente al salir
    
    Transaction Handling:
        Por defecto, cada statement se ejecuta en su propia transacción.
        Para transacciones explícitas:
        >>> async with get_db() as conn:
        ...     async with conn.transaction():
        ...         await conn.execute("INSERT INTO cliente ...")
        ...         await conn.execute("INSERT INTO cuenta ...")
        ...         # Commit automático si no hay excepciones
        ...         # Rollback automático si hay excepciones
    
    Query Methods Available:
        - conn.fetch(sql, *args): Retorna lista de records
        - conn.fetchrow(sql, *args): Retorna un solo record
        - conn.fetchval(sql, *args): Retorna un solo valor
        - conn.execute(sql, *args): Ejecuta sin retornar datos
        - conn.executemany(sql, args_list): Batch inserts
    
    Example (CRUD Operations):
        >>> # SELECT
        >>> async with get_db() as conn:
        ...     clientes = await conn.fetch(
        ...         "SELECT * FROM cliente WHERE id_cliente = $1",
        ...         cliente_id
        ...     )
        >>>
        >>> # INSERT
        >>> async with get_db() as conn:
        ...     row = await conn.fetchrow(
        ...         "INSERT INTO cliente (nombre, documento) "
        ...         "VALUES ($1, $2) RETURNING *",
        ...         "Juan Pérez", "12345678"
        ...     )
        >>>
        >>> # UPDATE
        >>> async with get_db() as conn:
        ...     await conn.execute(
        ...         "UPDATE cliente SET nombre = $1 WHERE id_cliente = $2",
        ...         "Juan Pérez M.", cliente_id
        ...     )
        >>>
        >>> # DELETE
        >>> async with get_db() as conn:
        ...     await conn.execute(
        ...         "DELETE FROM cliente WHERE id_cliente = $1",
        ...         cliente_id
        ...     )
    
    Security:
        - Usa prepared statements automáticamente ($1, $2, ...)
        - Previene SQL injection
        - Parámetros escapados automáticamente
    
    Error Handling:
        >>> try:
        ...     async with get_db() as conn:
        ...         await conn.execute("INVALID SQL")
        ... except asyncpg.PostgresError as e:
        ...     print(f"Database error: {e}")
    
    Performance:
        - La conexión se obtiene del pool (no se crea nueva)
        - Reutilización instantánea para el siguiente request
        - Bajo overhead comparado con crear conexiones nuevas
    
    Note:
        - Siempre usa el context manager (async with)
        - No cierres manualmente la conexión
        - El pool maneja el lifecycle automáticamente
    """
    # Obtener pool (se crea automáticamente si no existe)
    pool = await get_pool()
    
    # Adquirir una conexión del pool
    async with pool.acquire() as connection:
        # Yield la conexión al código que usa el context manager
        yield connection
        # La conexión se libera automáticamente al salir del bloque
        # (incluso si hay excepciones)
