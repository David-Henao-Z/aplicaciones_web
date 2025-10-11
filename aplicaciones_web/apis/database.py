# database.py
# ============================================================================
# Configuración y conexión a la base de datos PostgreSQL
# ============================================================================

import os
from dotenv import load_dotenv
import asyncpg
from contextlib import asynccontextmanager

# Cargar variables de entorno
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/testdb")

if not DATABASE_URL or DATABASE_URL == "postgresql://user:pass@localhost/testdb":
    print("⚠️  Usando configuración de base de datos temporal - Solo para testing")

# Pool de conexiones global
_pool = None


async def get_pool():
    """Obtiene el pool de conexiones"""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)
    return _pool


async def close_pool():
    """Cierra el pool de conexiones"""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


@asynccontextmanager
async def get_db():
    """Context manager para obtener una conexión de la base de datos"""
    pool = await get_pool()
    async with pool.acquire() as connection:
        yield connection
