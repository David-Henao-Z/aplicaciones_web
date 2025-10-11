"""
auth.py
Módulo para autenticación y generación de tokens JWT.
"""

from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel

# Configuración básica
SECRET_KEY = "Prueba123"  # Cambiar por una clave segura en producción
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class Token(BaseModel):
    """Estructura del token JWT retornado."""
    access_token: str
    token_type: str


class TokenData(BaseModel):
    """Datos decodificados desde el token JWT."""
    username: str | None = None


class User(BaseModel):
    """Usuario base del sistema."""
    username: str
    full_name: str | None = None
    disabled: bool | None = None


class UserInDB(User):
    """Usuario almacenado en la base de datos."""
    hashed_password: str


# Base de usuarios temporal (luego reemplazamos con PostgreSQL)
fake_users_db = {
    "admin@banco.com": {
        "username": "admin@banco.com",
        "full_name": "Administrador Banco",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPVeZ6HGH",  # admin123
        "disabled": False,
    }
}


def verify_password(plain_password, hashed_password):
    """Verifica si la contraseña coincide con el hash almacenado."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    """Genera el hash de una contraseña."""
    return pwd_context.hash(password)


def get_user(db, username: str):
    """Obtiene un usuario desde la base de datos simulada."""
    if username in db:
        user_dict = db[username]
        return UserInDB(**user_dict)
    return None


def authenticate_user(db, username: str, password: str):
    """Autentica credenciales de usuario."""
    user = get_user(db, username)
    if not user or not verify_password(password, user.hashed_password):
        return False
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    """Genera un JWT firmado."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Obtiene el usuario autenticado desde el token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar el token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception

    user = get_user(fake_users_db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user
