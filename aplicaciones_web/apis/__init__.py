"""Inicializador del paquete `aplicaciones_web`.

Este archivo convierte la carpeta en un paquete Python para que los
imports como `aplicaciones_web.apis.crud` funcionen al ejecutar
uvicorn desde la raíz del proyecto.

Al añadir este fichero evitamos errores de importación cuando se arranca
el servidor desde un directorio superior.
"""

__all__ = ["apis"]
