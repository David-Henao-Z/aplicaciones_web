import time
import os
from pathlib import Path
from fastapi import Request

# Determinar una ruta estable para los logs dentro del paquete.
# logs/ se creará en la raíz del paquete `aplicaciones_web`.
pkg = Path(__file__).resolve().parents[1]
LOG_DIR = pkg / "logs"
os.makedirs(LOG_DIR, exist_ok=True)
AUDIT_LOG = str(LOG_DIR / "audit.log")


async def audit_middleware(request: Request, call_next):
    """Middleware ligero de auditoría.

    Registra en un fichero cada petición HTTP con: timestamp, IP cliente,
    método, ruta, código de estado y duración en segundos.

    Se implementa de forma no intrusiva: si el log falla no se interrumpe
    el procesamiento de la petición.
    """
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    line = (
        f"{time.strftime('%Y-%m-%d %H:%M:%S')} | "
        f"{request.client.host if request.client else 'unknown'} | "
        f"{request.method} {request.url.path} | status={response.status_code} | "
        f"time={duration:.3f}s\n"
    )
    try:
        # Abrir en modo append; AUDIT_LOG puede ser un Path
        with open(AUDIT_LOG, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        # No interrumpir la petición si falla el logging
        pass
    return response
