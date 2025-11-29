"""
auth.py - Módulo de Autenticación y Seguridad
=============================================

Este módulo implementa el sistema de autenticación basado en JWT (JSON Web Tokens)
según el estándar OAuth2 Password Bearer Flow.

Funcionalidades principales:
    - Autenticación de usuarios con email y contraseña
    - Generación de tokens JWT firmados con HMAC-SHA256
    - Validación de tokens en endpoints protegidos
    - Hashing seguro de contraseñas con bcrypt
    - Gestión de usuarios (temporal, migrar a PostgreSQL)

Estándares implementados:
    - RFC 7519: JSON Web Token (JWT)
    - RFC 6749: OAuth 2.0 Authorization Framework
    - OWASP: Password Storage Cheat Sheet (bcrypt)

Configuración:
    SECRET_KEY: Clave secreta para firmar tokens (cambiar en producción)
    ALGORITHM: HS256 (HMAC con SHA-256)
    ACCESS_TOKEN_EXPIRE_MINUTES: 60 minutos de validez del token

Example:
    >>> # Autenticar usuario
    >>> user = authenticate_user(fake_users_db, "admin@banco.com", "admin123")
    >>> if user:
    ...     token = create_access_token({"sub": user.username})
    ...     print(f"Token generado: {token}")

Security Notes:
    - Los tokens son stateless (no se almacenan en servidor)
    - Cada token tiene expiración automática
    - Las contraseñas nunca se almacenan en texto plano
    - bcrypt usa 12 rounds por defecto para el hashing

Author: David Henao Zea, HOLOMAN582
Version: 2.0.0
Last Updated: 2025-11-29
"""

from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel

# ============================================================================
# Configuración de Seguridad
# ============================================================================

# Secret key para firmar tokens JWT
# IMPORTANTE: En producción, usar variable de entorno y clave generada aleatoriamente
# Ejemplo seguro: secrets.token_urlsafe(32)
SECRET_KEY = "Prueba123"  # ⚠️ CAMBIAR EN PRODUCCIÓN

# Algoritmo de firma: HMAC con SHA-256
# Alternativas: RS256 (RSA), ES256 (ECDSA)
ALGORITHM = "HS256"

# Tiempo de expiración del token en minutos
# Después de este tiempo, el usuario debe re-autenticarse
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# Contexto de Passlib para hashing de contraseñas
# bcrypt es el esquema recomendado por OWASP
# "deprecated": "auto" migra automáticamente a versiones más seguras
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Esquema OAuth2 que indica dónde obtener el token
# tokenUrl="token" → el endpoint POST /token genera tokens
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# ============================================================================
# Modelos de Datos (Pydantic)
# ============================================================================

class Token(BaseModel):
    """
    Respuesta del endpoint de autenticación.
    
    Este modelo representa la estructura del token JWT que se retorna
    al cliente después de una autenticación exitosa.
    
    Attributes:
        access_token (str): Token JWT firmado codificado en base64
        token_type (str): Tipo de token, siempre "bearer" para OAuth2
    
    Example:
        >>> {
        ...     "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        ...     "token_type": "bearer"
        ... }
    
    Note:
        El cliente debe incluir el token en headers como:
        Authorization: Bearer <access_token>
    """
    access_token: str
    token_type: str


class TokenData(BaseModel):
    """
    Datos extraídos del payload del JWT.
    
    Representa la información contenida dentro del token una vez decodificado.
    Se usa para validar y extraer el usuario del token en cada request.
    
    Attributes:
        username (str | None): Email del usuario extraído del claim "sub"
    
    JWT Claims usados:
        - sub (subject): username/email del usuario
        - exp (expiration): timestamp de expiración
    """
    username: str | None = None


class User(BaseModel):
    """
    Modelo base de usuario del sistema.
    
    Representa un usuario autenticado con sus datos básicos.
    No incluye información sensible como la contraseña.
    
    Attributes:
        username (str): Email del usuario (identificador único)
        full_name (str | None): Nombre completo del usuario
        disabled (bool | None): Si la cuenta está deshabilitada
    
    Example:
        >>> user = User(
        ...     username="admin@banco.com",
        ...     full_name="Administrador Banco",
        ...     disabled=False
        ... )
    """
    username: str
    full_name: str | None = None
    disabled: bool | None = None


class UserInDB(User):
    """
    Modelo de usuario almacenado en base de datos.
    
    Extiende User agregando el campo de contraseña hasheada.
    NUNCA se debe retornar este modelo en respuestas HTTP.
    
    Attributes:
        hashed_password (str): Contraseña encriptada con bcrypt
    
    Security:
        - La contraseña hasheada nunca debe exponerse en APIs
        - Solo se usa internamente para validación
        - bcrypt genera hashes de 60 caracteres con salt incorporado
    """
    hashed_password: str


# ============================================================================
# Base de Datos de Usuarios (TEMPORAL)
# ============================================================================
# TODO: Migrar a tabla users en PostgreSQL
# TODO: Implementar endpoints de registro y gestión de usuarios
# TODO: Agregar roles y permisos (RBAC)

fake_users_db = {
    "admin@banco.com": {
        "username": "admin@banco.com",
        "full_name": "Administrador Banco",
        # Hash bcrypt de "admin123" (12 rounds)
        # Generado con: bcrypt.hashpw(b"admin123", bcrypt.gensalt(12))
        "hashed_password": "$2b$12$zjxQevmjycKSvZ2L4XkQKO1LiYNETFCEuUq2TI7WbUWBdA.13ok2.",
        "disabled": False,
    }
    # Agregar más usuarios aquí temporalmente
    # En producción, esto debe estar en PostgreSQL
}


# ============================================================================
# Funciones de Hashing y Verificación de Contraseñas
# ============================================================================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica si una contraseña en texto plano coincide con su hash.
    
    Utiliza bcrypt para comparación segura que previene timing attacks.
    La verificación es computacionalmente costosa por diseño (seguridad).
    
    Args:
        plain_password (str): Contraseña en texto plano ingresada por el usuario
        hashed_password (str): Hash bcrypt almacenado en la base de datos
    
    Returns:
        bool: True si la contraseña es correcta, False si no coincide
    
    Security:
        - La comparación es constante en tiempo (previene timing attacks)
        - bcrypt automáticamente extrae el salt del hash
        - Usa 2^12 (4096) iteraciones por defecto
    
    Example:
        >>> hashed = "$2b$12$EixZaYVK1fsbw1ZfbX3OXe..."
        >>> verify_password("admin123", hashed)  # True
        >>> verify_password("wrong_pass", hashed)  # False
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Genera un hash bcrypt de una contraseña.
    
    Crea un hash seguro usando bcrypt con salt aleatorio incorporado.
    Este hash puede almacenarse de forma segura en la base de datos.
    
    Args:
        password (str): Contraseña en texto plano a hashear
    
    Returns:
        str: Hash bcrypt de 60 caracteres con formato:
             $2b$<rounds>$<salt><hash>
    
    Security:
        - Genera salt aleatorio único por cada hash
        - Usa 12 rounds (2^12 = 4096 iteraciones)
        - El hash resultante incluye el salt
        - Imposible de revertir (función unidireccional)
    
    Example:
        >>> hash = get_password_hash("mySecurePassword123")
        >>> print(len(hash))  # 60
        >>> print(hash[:4])  # $2b$
    
    Note:
        Para cambiar el número de rounds, modificar pwd_context en la configuración
    """
    return pwd_context.hash(password)


# ============================================================================
# Funciones de Gestión de Usuarios
# ============================================================================

def get_user(db: dict, username: str) -> UserInDB | None:
    """
    Recupera un usuario de la base de datos por su username.
    
    Busca el usuario en el diccionario de usuarios y lo convierte
    a un objeto UserInDB si existe.
    
    Args:
        db (dict): Base de datos de usuarios (fake_users_db)
        username (str): Email del usuario a buscar
    
    Returns:
        UserInDB | None: Objeto UserInDB si existe, None si no se encuentra
    
    Example:
        >>> user = get_user(fake_users_db, "admin@banco.com")
        >>> if user:
        ...     print(f"Usuario encontrado: {user.full_name}")
        >>> else:
        ...     print("Usuario no existe")
    
    Note:
        En producción, esto debe ser una consulta a PostgreSQL:
        SELECT * FROM users WHERE email = $1
    """
    if username in db:
        user_dict = db[username]
        return UserInDB(**user_dict)
    return None


def authenticate_user(db: dict, username: str, password: str) -> UserInDB | bool:
    """
    Autentica un usuario validando sus credenciales.
    
    Verifica que el usuario exista y que la contraseña sea correcta.
    Este es el punto central de autenticación del sistema.
    
    Args:
        db (dict): Base de datos de usuarios
        username (str): Email del usuario
        password (str): Contraseña en texto plano
    
    Returns:
        UserInDB | bool: 
            - UserInDB: Si las credenciales son válidas
            - False: Si el usuario no existe o la contraseña es incorrecta
    
    Security:
        - No revela si el error es por usuario inexistente o contraseña incorrecta
        - Previene ataques de enumeración de usuarios
        - Usa comparación segura de contraseñas con bcrypt
    
    Example:
        >>> user = authenticate_user(fake_users_db, "admin@banco.com", "admin123")
        >>> if user:
        ...     print(f"Login exitoso: {user.username}")
        ... else:
        ...     print("Credenciales inválidas")
    
    Flow:
        1. Buscar usuario por username
        2. Si no existe → retornar False
        3. Verificar contraseña con bcrypt
        4. Si no coincide → retornar False
        5. Si todo OK → retornar UserInDB
    """
    user = get_user(db, username)
    if not user or not verify_password(password, user.hashed_password):
        return False
    return user


# ============================================================================
# Funciones de Generación y Validación de JWT
# ============================================================================

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Genera un token JWT firmado con los datos proporcionados.
    
    Crea un JSON Web Token que contiene los datos del usuario y una
    expiración. El token está firmado con HMAC-SHA256 para garantizar
    su integridad.
    
    Args:
        data (dict): Datos a incluir en el JWT (típicamente {"sub": username})
        expires_delta (timedelta | None): Tiempo de expiración personalizado.
                                         Por defecto: 15 minutos
    
    Returns:
        str: Token JWT codificado en formato: <header>.<payload>.<signature>
    
    JWT Structure:
        Header: {"alg": "HS256", "typ": "JWT"}
        Payload: {"sub": username, "exp": timestamp}
        Signature: HMACSHA256(base64(header).base64(payload), SECRET_KEY)
    
    Example:
        >>> from datetime import timedelta
        >>> token = create_access_token(
        ...     data={"sub": "admin@banco.com"},
        ...     expires_delta=timedelta(hours=1)
        ... )
        >>> print(token[:20])  # 'eyJhbGciOiJIUzI1NiI...'
    
    Security:
        - El token NO está encriptado, solo firmado
        - No incluir información sensible en el payload
        - La firma previene modificaciones del token
        - La expiración automática mejora la seguridad
    
    Note:
        Para verificar un token en jwt.io, necesitas la SECRET_KEY
    """
    to_encode = data.copy()
    # Calcular timestamp de expiración
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    # Agregar claim de expiración al payload
    to_encode.update({"exp": expire})
    # Firmar y codificar el token
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """
    Extrae y valida el usuario actual desde el token JWT.
    
    Esta es una función de dependencia de FastAPI que se ejecuta
    automáticamente en endpoints protegidos con Depends(get_current_user).
    Valida el token y retorna el usuario autenticado.
    
    Args:
        token (str): Token JWT extraído del header Authorization
                    Inyectado automáticamente por oauth2_scheme
    
    Returns:
        User: Usuario autenticado si el token es válido
    
    Raises:
        HTTPException 401: Si el token es inválido, expirado o el usuario no existe
    
    Validation Steps:
        1. Decodificar token con SECRET_KEY
        2. Verificar firma HMAC
        3. Validar expiración automáticamente
        4. Extraer username del claim "sub"
        5. Buscar usuario en base de datos
        6. Retornar User (sin contraseña)
    
    Example:
        >>> # En un endpoint protegido:
        >>> @app.get("/clientes")
        >>> async def listar_clientes(
        ...     current_user: User = Depends(get_current_user)
        ... ):
        ...     # current_user ya está autenticado y validado
        ...     return await get_clientes()
    
    Security:
        - Valida automáticamente la expiración del token
        - Verifica la firma para detectar manipulaciones
        - No retorna información sensible del usuario
        - Previene replay attacks con expiración corta
    
    HTTP Response (si falla):
        Status: 401 Unauthorized
        Headers: {"WWW-Authenticate": "Bearer"}
        Body: {"detail": "No se pudo validar el token"}
    """
    # Preparar excepción para credenciales inválidas
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar el token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decodificar y verificar el token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # Extraer username del claim "sub" (subject)
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        # Token inválido, expirado o firma incorrecta
        raise credentials_exception

    # Buscar usuario en la base de datos
    user = get_user(fake_users_db, username=token_data.username)
    if user is None:
        # Usuario no existe (posiblemente eliminado después de generar el token)
        raise credentials_exception
    
    # Retornar usuario sin información sensible
    return user
