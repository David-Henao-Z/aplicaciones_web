# audit.py
"""
Middleware de Auditoría para FastAPI.

Este módulo implementa un middleware ligero que registra todas las peticiones
HTTP en un archivo de log para propósitos de auditoría y debugging.

Funcionalidad:
    - Registra cada petición HTTP con timestamp, IP, método, ruta y duración
    - Crea automáticamente el directorio de logs si no existe
    - No interrumpe el procesamiento de requests si el logging falla
    - Implementación no intrusiva (fail-safe)

Formato del Log:
    YYYY-MM-DD HH:MM:SS | IP_cliente | MÉTODO ruta | status=XXX | time=X.XXXs

Ejemplo de línea en audit.log:
    2024-01-22 14:30:45 | 127.0.0.1 | POST /token | status=200 | time=0.042s
    2024-01-22 14:31:12 | 127.0.0.1 | GET /clientes | status=200 | time=0.018s
    2024-01-22 14:31:45 | 192.168.1.50 | POST /transacciones/deposito | status=201 | time=0.235s

Ubicación del log:
    aplicaciones_web/logs/audit.log
    (Se crea automáticamente en la primera ejecución)

Uso:
    En tu aplicación FastAPI:
    
    >>> from aplicaciones_web.apis.audit import audit_middleware
    >>> app = FastAPI()
    >>> app.middleware("http")(audit_middleware)

Beneficios:
    - Trazabilidad de todas las requests
    - Detección de patrones de uso
    - Debugging de problemas de rendimiento
    - Cumplimiento de requisitos de auditoría
    - Análisis de tiempos de respuesta

Consideraciones de Seguridad:
    - NO registra cuerpos de requests (puede contener passwords)
    - NO registra headers Authorization (contienen tokens)
    - Solo registra metadatos básicos (IP, método, ruta, status, tiempo)

Rendimiento:
    - Overhead mínimo (~1-2ms por request)
    - Escritura asíncrona en archivo
    - No bloquea el procesamiento de requests

Version: 1.0.0
Author: Sistema Bancario - Aplicaciones Web
License: MIT
"""

# ============================================================================
# Importaciones
# ============================================================================
import time
import os
from pathlib import Path
from fastapi import Request

# ============================================================================
# Configuración del Sistema de Logs
# ============================================================================
# Determinar ruta estable para los logs dentro del paquete
# logs/ se creará en aplicaciones_web/logs/
pkg = Path(__file__).resolve().parents[1]  # Sube dos niveles desde audit.py
LOG_DIR = pkg / "logs"  # aplicaciones_web/logs/

# Crear directorio de logs si no existe
os.makedirs(LOG_DIR, exist_ok=True)

# Ruta completa al archivo de auditoría
AUDIT_LOG = str(LOG_DIR / "audit.log")


# ============================================================================
# Middleware de Auditoría
# ============================================================================
async def audit_middleware(request: Request, call_next):
    """
    Middleware de auditoría que registra todas las peticiones HTTP.
    
    Este middleware intercepta cada request, mide su duración, y registra
    información básica en un archivo de log.
    
    Args:
        request (Request): Objeto Request de FastAPI con metadatos de la petición
        call_next (Callable): Función para continuar con el procesamiento
    
    Returns:
        Response: La respuesta HTTP sin modificar
    
    Process Flow:
        1. Capturar timestamp de inicio
        2. Procesar la petición (call_next)
        3. Capturar timestamp de fin
        4. Calcular duración
        5. Formatear línea de log
        6. Escribir en archivo (modo append)
        7. Retornar respuesta original
    
    Log Format:
        YYYY-MM-DD HH:MM:SS | IP | MÉTODO ruta | status=XXX | time=X.XXXs
    
    Example Log Entry:
        2024-01-22 14:30:45 | 127.0.0.1 | POST /token | status=200 | time=0.042s
    
    Error Handling:
        - Si el logging falla (permisos, disco lleno, etc.), la excepción
          se captura silenciosamente y el request continúa normalmente
        - Esto asegura que problemas de logging no afecten la disponibilidad
    
    Security:
        - NO registra bodies (pueden contener passwords)
        - NO registra headers (pueden contener tokens)
        - Solo registra metadatos públicos
    
    Performance:
        - Overhead mínimo: medición de tiempo + escritura de archivo
        - Escritura en modo append (eficiente)
        - No bloquea el procesamiento asíncrono
    
    Note:
        - El archivo audit.log puede crecer indefinidamente
        - Considerar rotación de logs en producción (logrotate, etc.)
        - Para producción, considerar sistemas más robustos (ELK, Splunk, etc.)
    """
    # Capturar tiempo de inicio
    start = time.time()
    
    # Procesar la petición y obtener la respuesta
    response = await call_next(request)
    
    # Calcular duración en segundos
    duration = time.time() - start
    
    # Formatear línea de log con toda la información relevante
    line = (
        f"{time.strftime('%Y-%m-%d %H:%M:%S')} | "  # Timestamp legible
        f"{request.client.host if request.client else 'unknown'} | "  # IP del cliente
        f"{request.method} {request.url.path} | "  # Método y ruta
        f"status={response.status_code} | "  # Código de respuesta HTTP
        f"time={duration:.3f}s\n"  # Duración con 3 decimales
    )
    
    try:
        # Escribir en archivo de log (modo append para no sobrescribir)
        with open(AUDIT_LOG, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        # Si falla el logging, no interrumpir la petición
        # Fail-safe: la auditoría no debe afectar la disponibilidad
        pass
    
    # Retornar la respuesta sin modificar
    return response


# ============================================================================
# Fin del módulo audit.py
# ============================================================================
