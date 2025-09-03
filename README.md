# Aplicaciones Web - Curso Python & FastAPI

Proyecto para aprender desarrollo de APIs REST con Python y FastAPI.

## Características

- **API de Usuarios**: CRUD completo para gestión de usuarios
- **API de Blog**: Sistema completo con usuarios, posts y comentarios
- **Documentación automática**: Swagger UI integrado
- **Validación de datos**: Usando Pydantic

## Requisitos

- Python **3.10+**
- `pip`

## Instalación

```bash
# Clonar repositorio
git clone <https://github.com/David-Henao-Z/aplicaciones_web>
cd aplicaciones_web

# Instalar dependencias
pip install fastapi uvicorn pydantic

# Ejecutar API de usuarios
uvicorn apis.main:app --reload

## Uso

- **Documentación**: `http://localhost:8000/docs`
- **API Usuarios**: Endpoints CRUD en `/users`
- **API Blog**: Posts, comentarios y búsqueda

## Estructura

apis
main.py      # API básica de usuarios
blog_api.py  # API completa de blog del profesor
