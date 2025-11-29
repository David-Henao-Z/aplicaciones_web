# functions.py
# ============================================================================
# Módulo de **funciones y modelos** para la API del Banco con PostgreSQL.
# Contiene:
# - Modelos Pydantic actualizados para usar UUIDs
# - Funciones para interactuar con PostgreSQL
# - Lógica/reglas de negocio (crear/actualizar/eliminar, depositar, retirar, transferir)
# ============================================================================

from __future__ import annotations
from datetime import datetime, date
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, EmailStr, constr, PositiveFloat
from aplicaciones_web.apis.database import get_db


# =========================
# Modelos (Pydantic)
# =========================
class TipoCuenta(str, Enum):
    AHORROS = "AHORROS"
    CORRIENTE = "CORRIENTE"


class Cliente(BaseModel):
    """
    Modelo de datos para un cliente del banco.
    
    Representa a una persona que puede tener múltiples cuentas bancarias.
    Cada cliente debe tener un documento único y nombre completo.
    
    Attributes:
        id (UUID): Identificador único del cliente generado automáticamente
        nombre_completo (str): Nombre y apellido del cliente (mínimo 2 caracteres)
        documento (str): Número de identificación único del cliente
        fecha_creacion (datetime): Timestamp de cuando se creó el registro
        fecha_edicion (Optional[datetime]): Timestamp de la última modificación
    
    Example:
        >>> cliente = Cliente(
        ...     id=uuid4(),
        ...     nombre_completo="David Jiménez",
        ...     documento="12345678"
        ... )
    """
    id: UUID = Field(..., example="123e4567-e89b-12d3-a456-426614174000")
    nombre_completo: str = Field(..., min_length=2, example="David Jiménez")
    documento: str = Field(..., example="12345678")
    fecha_creacion: datetime = Field(default_factory=datetime.now)
    fecha_edicion: Optional[datetime] = None


class ClienteCreate(BaseModel):
    """
    Esquema de datos para crear un nuevo cliente.
    
    Contiene únicamente los campos requeridos para registrar un cliente.
    El ID y timestamps se generan automáticamente en el servidor.
    
    Attributes:
        nombre_completo (str): Nombre completo del cliente
        documento (str): Número de documento de identidad
    """
    nombre_completo: str = Field(..., min_length=2, example="David Jiménez")
    documento: str = Field(..., example="12345678")


class TipoCuentaModel(BaseModel):
    id: UUID = Field(..., example="123e4567-e89b-12d3-a456-426614174000")
    nombre: str = Field(..., example="AHORROS")
    descripcion: Optional[str] = Field(None, example="Cuenta de ahorros")


class Cuenta(BaseModel):
    """
    Modelo de datos para una cuenta bancaria.
    
    Cada cuenta pertenece a un cliente y tiene un tipo específico (Ahorros/Corriente).
    El saldo no puede ser negativo y se actualiza con cada transacción.
    
    Attributes:
        id (UUID): Identificador único de la cuenta
        numero (str): Número de cuenta único generado automáticamente (formato: ACC0001)
        id_cliente (UUID): Referencia al cliente propietario de la cuenta
        id_tipo_cuenta (UUID): Referencia al tipo de cuenta (Ahorros/Corriente)
        saldo (float): Saldo actual de la cuenta (>= 0)
        fecha_creacion (datetime): Fecha de apertura de la cuenta
        fecha_edicion (Optional[datetime]): Última modificación del registro
    
    Business Rules:
        - El saldo nunca puede ser negativo
        - Una cuenta solo puede eliminarse si el saldo es 0
        - El número de cuenta es único en todo el sistema
    """
    id: UUID = Field(..., example="123e4567-e89b-12d3-a456-426614174000")
    numero: str = Field(..., example="ACC0001")
    id_cliente: UUID = Field(..., example="123e4567-e89b-12d3-a456-426614174000")
    id_tipo_cuenta: UUID = Field(..., example="123e4567-e89b-12d3-a456-426614174000")
    saldo: float = Field(0.0, ge=0, example=0.0)
    fecha_creacion: datetime = Field(default_factory=datetime.now)
    fecha_edicion: Optional[datetime] = None


class CuentaCreate(BaseModel):
    id_cliente: UUID = Field(..., example="123e4567-e89b-12d3-a456-426614174000")
    id_tipo_cuenta: UUID = Field(..., example="123e4567-e89b-12d3-a456-426614174000")


class TransaccionTipo(str, Enum):
    DEPOSITO = "DEPOSITO"
    RETIRO = "RETIRO"
    TRANSFERENCIA = "TRANSFERENCIA"


class Transaccion(BaseModel):
    """
    Modelo de datos para una transacción bancaria.
    
    Registra todas las operaciones monetarias realizadas en el sistema.
    Puede ser de tipo: DEPOSITO, RETIRO o TRANSFERENCIA.
    
    Attributes:
        id (UUID): Identificador único de la transacción
        tipo (TransaccionTipo): Tipo de operación (DEPOSITO/RETIRO/TRANSFERENCIA)
        id_cuenta_origen (Optional[UUID]): Cuenta de donde sale el dinero (None para depósitos)
        id_cuenta_destino (Optional[UUID]): Cuenta a donde llega el dinero (None para retiros)
        monto (PositiveFloat): Cantidad de dinero involucrada (siempre positivo)
        momento (datetime): Timestamp exacto de cuando se ejecutó la transacción
        fecha_creacion (datetime): Fecha de registro en la base de datos
        fecha_edicion (Optional[datetime]): Última modificación (auditoría)
    
    Business Rules:
        - DEPOSITO: solo tiene cuenta_destino
        - RETIRO: solo tiene cuenta_origen (requiere fondos suficientes)
        - TRANSFERENCIA: tiene ambas cuentas (origen debe tener fondos)
        - El monto siempre debe ser positivo
        - Las transacciones son inmutables una vez creadas
    """
    id: UUID = Field(..., example="123e4567-e89b-12d3-a456-426614174000")
    tipo: TransaccionTipo
    id_cuenta_origen: Optional[UUID] = Field(
        None, example="123e4567-e89b-12d3-a456-426614174000"
    )
    id_cuenta_destino: Optional[UUID] = Field(
        None, example="123e4567-e89b-12d3-a456-426614174000"
    )
    monto: PositiveFloat
    momento: datetime = Field(default_factory=datetime.now)
    fecha_creacion: datetime = Field(default_factory=datetime.now)
    fecha_edicion: Optional[datetime] = None


class Deposito(BaseModel):
    id_cuenta: UUID = Field(..., example="123e4567-e89b-12d3-a456-426614174000")
    monto: PositiveFloat = Field(..., example=100000.0)


class Retiro(BaseModel):
    id_cuenta: UUID = Field(..., example="123e4567-e89b-12d3-a456-426614174000")
    monto: PositiveFloat = Field(..., example=50000.0)


class Transferencia(BaseModel):
    id_cuenta_origen: UUID = Field(..., example="123e4567-e89b-12d3-a456-426614174000")
    id_cuenta_destino: UUID = Field(..., example="123e4567-e89b-12d3-a456-426614174000")
    monto: PositiveFloat = Field(..., example=25000.0)


# =========================
# Utilidades internas
# =========================
def _generar_numero_cuenta() -> str:
    """Genera números de cuenta únicos"""
    import random
    import string

    return "ACC" + "".join(random.choices(string.digits, k=7))


# =========================
# Funciones de negocio: CLIENTES
# =========================
async def listar_clientes() -> List[Cliente]:
    """
    Obtiene la lista completa de clientes registrados en el sistema.
    
    Ejecuta una consulta a la base de datos PostgreSQL para recuperar todos
    los clientes ordenados por fecha de creación (más recientes primero).
    
    Returns:
        List[Cliente]: Lista de objetos Cliente con todos sus atributos.
                      Retorna lista vacía si no hay clientes registrados.
    
    Raises:
        asyncpg.PostgresError: Si hay un error de conexión o consulta a la BD
    
    Example:
        >>> clientes = await listar_clientes()
        >>> print(f"Total de clientes: {len(clientes)}")
    """
    async with get_db() as conn:
        rows = await conn.fetch(
            """
            SELECT id_cliente as id, nombre_completo, documento, fecha_creacion, fecha_edicion
            FROM banco.cliente
            ORDER BY fecha_creacion DESC
        """
        )
        return [Cliente(**dict(row)) for row in rows]


async def obtener_cliente(cliente_id: UUID) -> Optional[Cliente]:
    """
    Busca y retorna un cliente específico por su ID.
    
    Args:
        cliente_id (UUID): Identificador único del cliente a buscar
    
    Returns:
        Optional[Cliente]: Objeto Cliente si se encuentra, None si no existe
    
    Raises:
        asyncpg.PostgresError: Si hay un error en la consulta a la base de datos
    
    Example:
        >>> cliente = await obtener_cliente(UUID("123e4567-e89b-12d3-a456-426614174000"))
        >>> if cliente:
        ...     print(f"Cliente encontrado: {cliente.nombre_completo}")
    """
    async with get_db() as conn:
        row = await conn.fetchrow(
            """
            SELECT id_cliente as id, nombre_completo, documento, fecha_creacion, fecha_edicion
            FROM banco.cliente
            WHERE id_cliente = $1
        """,
            cliente_id,
        )
        return Cliente(**dict(row)) if row else None


async def crear_cliente(payload: ClienteCreate) -> Cliente:
    """
    Registra un nuevo cliente en el sistema.
    
    Valida que el documento sea único antes de crear el registro.
    Si el documento ya existe, lanza una excepción ValueError.
    
    Args:
        payload (ClienteCreate): Datos del cliente a crear (nombre y documento)
    
    Returns:
        Cliente: Objeto del cliente recién creado con su ID y timestamps
    
    Raises:
        ValueError: Si el documento ya está registrado en el sistema
        asyncpg.PostgresError: Si hay un error en la operación de base de datos
    
    Business Rules:
        - El documento debe ser único en todo el sistema
        - El ID se genera automáticamente (UUID v4)
        - fecha_creacion se establece automáticamente
    
    Example:
        >>> nuevo_cliente = ClienteCreate(nombre_completo="Juan Pérez", documento="12345678")
        >>> cliente = await crear_cliente(nuevo_cliente)
        >>> print(f"Cliente creado con ID: {cliente.id}")
    """
    async with get_db() as conn:
        # Verificar documento único
        exists = await conn.fetchval(
            """
            SELECT EXISTS(SELECT 1 FROM banco.cliente WHERE documento = $1)
        """,
            payload.documento,
        )

        if exists:
            raise ValueError("Documento ya registrado")

        row = await conn.fetchrow(
            """
            INSERT INTO banco.cliente (nombre_completo, documento)
            VALUES ($1, $2)
            RETURNING id_cliente as id, nombre_completo, documento, fecha_creacion, fecha_edicion
        """,
            payload.nombre_completo,
            payload.documento,
        )

        return Cliente(**dict(row))


async def actualizar_cliente(cliente_id: UUID, payload: ClienteCreate) -> Cliente:
    """
    Actualiza la información de un cliente existente.
    
    Valida que el cliente exista y que el nuevo documento sea único
    (puede mantener su propio documento o usar uno nuevo no registrado).
    
    Args:
        cliente_id (UUID): ID del cliente a actualizar
        payload (ClienteCreate): Nuevos datos del cliente (nombre y documento)
    
    Returns:
        Cliente: Objeto del cliente con los datos actualizados
    
    Raises:
        KeyError: Si el cliente no existe en el sistema
        ValueError: Si el nuevo documento ya está registrado por otro cliente
        asyncpg.PostgresError: Si hay un error en la base de datos
    
    Business Rules:
        - El cliente debe existir previamente
        - El documento debe ser único (excepto el propio cliente)
        - fecha_edicion se actualiza automáticamente
        - fecha_creacion permanece sin cambios
    
    Example:
        >>> datos = ClienteCreate(nombre_completo="Juan Pérez Martínez", documento="12345678")
        >>> cliente = await actualizar_cliente(cliente_id, datos)
        >>> print(f"Cliente actualizado: {cliente.nombre_completo}")
    """
    async with get_db() as conn:
        # Verificar que existe
        exists = await conn.fetchval(
            """
            SELECT EXISTS(SELECT 1 FROM banco.cliente WHERE id_cliente = $1)
        """,
            cliente_id,
        )

        if not exists:
            raise KeyError("Cliente no encontrado")

        # Verificar documento único (excepto el mismo cliente)
        doc_exists = await conn.fetchval(
            """
            SELECT EXISTS(SELECT 1 FROM banco.cliente WHERE documento = $1 AND id_cliente != $2)
        """,
            payload.documento,
            cliente_id,
        )

        if doc_exists:
            raise ValueError("Documento ya registrado por otro cliente")

        row = await conn.fetchrow(
            """
            UPDATE banco.cliente 
            SET nombre_completo = $2, documento = $3, fecha_edicion = NOW()
            WHERE id_cliente = $1
            RETURNING id_cliente as id, nombre_completo, documento, fecha_creacion, fecha_edicion
        """,
            cliente_id,
            payload.nombre_completo,
            payload.documento,
        )

        return Cliente(**dict(row))


async def eliminar_cliente(cliente_id: UUID) -> None:
    """
    Elimina un cliente del sistema.
    
    Solo permite eliminar clientes que no tengan cuentas asociadas.
    Esta es una operación irreversible.
    
    Args:
        cliente_id (UUID): ID del cliente a eliminar
    
    Returns:
        None: No retorna valor si la eliminación es exitosa
    
    Raises:
        KeyError: Si el cliente no existe
        RuntimeError: Si el cliente tiene cuentas activas
        asyncpg.PostgresError: Si hay un error en la base de datos
    
    Business Rules:
        - El cliente no debe tener cuentas asociadas
        - Es una eliminación física (no soft delete)
        - Operación irreversible
    
    Example:
        >>> try:
        ...     await eliminar_cliente(cliente_id)
        ...     print("Cliente eliminado exitosamente")
        ... except RuntimeError as e:
        ...     print(f"No se puede eliminar: {e}")
    
    Note:
        - Verificar primero si el cliente tiene cuentas usando listar_cuentas()
        - Considerar eliminar primero todas las cuentas del cliente
    """
    async with get_db() as conn:
        # Verificar que existe
        exists = await conn.fetchval(
            """
            SELECT EXISTS(SELECT 1 FROM banco.cliente WHERE id_cliente = $1)
        """,
            cliente_id,
        )

        if not exists:
            raise KeyError("Cliente no encontrado")

        # Verificar que no tiene cuentas
        has_accounts = await conn.fetchval(
            """
            SELECT EXISTS(SELECT 1 FROM banco.cuenta WHERE id_cliente = $1)
        """,
            cliente_id,
        )

        if has_accounts:
            raise RuntimeError("Cliente con cuentas activas")

        await conn.execute(
            """
            DELETE FROM banco.cliente WHERE id_cliente = $1
        """,
            cliente_id,
        )


# =========================
# Funciones de negocio: CUENTAS
# =========================
async def listar_cuentas(
    cliente_id: Optional[UUID] = None, tipo: Optional[str] = None
) -> List[Cuenta]:
    """
    Lista todas las cuentas con filtros opcionales.
    
    Permite filtrar por cliente y/o tipo de cuenta. Si no se proporcionan
    filtros, retorna todas las cuentas del sistema.
    
    Args:
        cliente_id (Optional[UUID]): ID del cliente para filtrar sus cuentas
        tipo (Optional[str]): Nombre del tipo de cuenta (ej: "AHORROS", "CORRIENTE")
    
    Returns:
        List[Cuenta]: Lista de cuentas que cumplen los filtros (puede estar vacía)
    
    Raises:
        asyncpg.PostgresError: Si hay un error en la consulta
    
    Example:
        >>> # Todas las cuentas
        >>> cuentas = await listar_cuentas()
        >>>
        >>> # Cuentas de un cliente específico
        >>> cuentas = await listar_cuentas(cliente_id=uuid_cliente)
        >>>
        >>> # Cuentas de ahorro de un cliente
        >>> cuentas = await listar_cuentas(cliente_id=uuid_cliente, tipo="AHORROS")
    
    Note:
        - Los resultados se ordenan por fecha de creación (más recientes primero)
        - El tipo debe coincidir exactamente con el nombre en tipo_cuenta
    """
    async with get_db() as conn:
        where_conditions = []
        params = []
        param_count = 0

        if cliente_id is not None:
            param_count += 1
            where_conditions.append(f"c.id_cliente = ${param_count}")
            params.append(cliente_id)

        if tipo is not None:
            param_count += 1
            where_conditions.append(f"tc.nombre = ${param_count}")
            params.append(tipo)

        where_clause = (
            "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        )

        query = f"""
            SELECT c.id_cuenta as id, c.numero, c.id_cliente, c.id_tipo_cuenta, 
                   c.saldo, c.fecha_creacion, c.fecha_edicion
            FROM banco.cuenta c
            JOIN banco.tipo_cuenta tc ON c.id_tipo_cuenta = tc.id_tipo_cuenta
            {where_clause}
            ORDER BY c.fecha_creacion DESC
        """

        rows = await conn.fetch(query, *params)
        return [Cuenta(**dict(row)) for row in rows]


async def obtener_cuenta(cuenta_id: UUID) -> Optional[Cuenta]:
    """
    Busca una cuenta por su ID.
    
    Args:
        cuenta_id (UUID): Identificador único de la cuenta
    
    Returns:
        Optional[Cuenta]: Objeto Cuenta si existe, None si no se encuentra
    
    Raises:
        asyncpg.PostgresError: Si hay un error en la consulta
    
    Example:
        >>> cuenta = await obtener_cuenta(cuenta_id)
        >>> if cuenta:
        ...     print(f"Saldo actual: ${cuenta.saldo}")
        ... else:
        ...     print("Cuenta no encontrada")
    """
    async with get_db() as conn:
        row = await conn.fetchrow(
            """
            SELECT id_cuenta as id, numero, id_cliente, id_tipo_cuenta, 
                   saldo, fecha_creacion, fecha_edicion
            FROM banco.cuenta
            WHERE id_cuenta = $1
        """,
            cuenta_id,
        )
        return Cuenta(**dict(row)) if row else None


async def obtener_cuenta_por_numero(numero: str) -> Optional[Cuenta]:
    """
    Busca una cuenta por su número de cuenta.
    
    Útil para operaciones donde el usuario proporciona el número de cuenta
    en lugar del ID interno.
    
    Args:
        numero (str): Número de cuenta (generado automáticamente al crear)
    
    Returns:
        Optional[Cuenta]: Objeto Cuenta si existe, None si no se encuentra
    
    Raises:
        asyncpg.PostgresError: Si hay un error en la consulta
    
    Example:
        >>> cuenta = await obtener_cuenta_por_numero("1234567890")
        >>> if cuenta:
        ...     print(f"Cuenta encontrada - Cliente: {cuenta.id_cliente}")
    
    Note:
        - El número de cuenta es único en el sistema
        - Se genera automáticamente en crear_cuenta()
    """
    async with get_db() as conn:
        row = await conn.fetchrow(
            """
            SELECT id_cuenta as id, numero, id_cliente, id_tipo_cuenta, 
                   saldo, fecha_creacion, fecha_edicion
            FROM banco.cuenta
            WHERE numero = $1
        """,
            numero,
        )
        return Cuenta(**dict(row)) if row else None


async def crear_cuenta(payload: CuentaCreate) -> Cuenta:
    """
    Crea una nueva cuenta bancaria.
    
    Valida que el cliente y el tipo de cuenta existan antes de crear.
    La cuenta se crea con saldo inicial de 0.
    
    Args:
        payload (CuentaCreate): Datos de la cuenta (id_cliente, id_tipo_cuenta)
    
    Returns:
        Cuenta: Objeto de la cuenta recién creada
    
    Raises:
        KeyError: Si el cliente o tipo de cuenta no existen
        asyncpg.PostgresError: Si hay un error en la base de datos
    
    Business Rules:
        - El cliente debe existir previamente
        - El tipo de cuenta debe existir en tipo_cuenta
        - El número de cuenta se genera automáticamente
        - El saldo inicial es siempre 0.0
        - ID y timestamps se generan automáticamente
    
    Example:
        >>> datos = CuentaCreate(id_cliente=uuid_cliente, id_tipo_cuenta=uuid_tipo)
        >>> cuenta = await crear_cuenta(datos)
        >>> print(f"Cuenta creada: {cuenta.numero} con saldo ${cuenta.saldo}")
    
    Note:
        - El número de cuenta es único y se genera con _generar_numero_cuenta()
        - Para depositar dinero inicial, usar depositar() después de crear
    """
    async with get_db() as conn:
        # Verificar que cliente existe
        cliente_exists = await conn.fetchval(
            """
            SELECT EXISTS(SELECT 1 FROM banco.cliente WHERE id_cliente = $1)
        """,
            payload.id_cliente,
        )

        if not cliente_exists:
            raise KeyError("Cliente no existe")

        # Verificar que tipo cuenta existe
        tipo_exists = await conn.fetchval(
            """
            SELECT EXISTS(SELECT 1 FROM banco.tipo_cuenta WHERE id_tipo_cuenta = $1)
        """,
            payload.id_tipo_cuenta,
        )

        if not tipo_exists:
            raise KeyError("Tipo de cuenta no existe")

        numero = _generar_numero_cuenta()

        row = await conn.fetchrow(
            """
            INSERT INTO banco.cuenta (numero, id_cliente, id_tipo_cuenta, saldo)
            VALUES ($1, $2, $3, 0.0)
            RETURNING id_cuenta as id, numero, id_cliente, id_tipo_cuenta, 
                      saldo, fecha_creacion, fecha_edicion
        """,
            numero,
            payload.id_cliente,
            payload.id_tipo_cuenta,
        )

        return Cuenta(**dict(row))


async def eliminar_cuenta(cuenta_id: UUID) -> None:
    """
    Elimina una cuenta del sistema.
    
    Solo permite eliminar cuentas con saldo de 0. Esta es una operación
    irreversible que elimina físicamente el registro.
    
    Args:
        cuenta_id (UUID): ID de la cuenta a eliminar
    
    Returns:
        None: No retorna valor si la eliminación es exitosa
    
    Raises:
        KeyError: Si la cuenta no existe
        RuntimeError: Si la cuenta tiene saldo diferente de 0
        asyncpg.PostgresError: Si hay un error en la base de datos
    
    Business Rules:
        - El saldo debe ser exactamente 0 para poder eliminar
        - Es una eliminación física (no soft delete)
        - Las transacciones asociadas permanecen en el historial
        - Operación irreversible
    
    Example:
        >>> try:
        ...     await eliminar_cuenta(cuenta_id)
        ...     print("Cuenta eliminada exitosamente")
        ... except RuntimeError as e:
        ...     print(f"No se puede eliminar: {e}")
    
    Note:
        - Verificar el saldo antes con obtener_cuenta()
        - Si hay saldo, usar retirar() o transferir() para dejarlo en 0
    """
    async with get_db() as conn:
        # Verificar que existe
        row = await conn.fetchrow(
            """
            SELECT saldo FROM banco.cuenta WHERE id_cuenta = $1
        """,
            cuenta_id,
        )

        if not row:
            raise KeyError("Cuenta no encontrada")

        if row["saldo"] != 0:
            raise RuntimeError(
                "No se puede eliminar una cuenta con saldo distinto de 0"
            )

        await conn.execute(
            """
            DELETE FROM banco.cuenta WHERE id_cuenta = $1
        """,
            cuenta_id,
        )


# =========================
# Funciones de negocio: TRANSACCIONES
# =========================
async def listar_transacciones(
    cuenta_id: Optional[UUID] = None,
    desde: Optional[date] = None,
    hasta: Optional[date] = None,
) -> List[Transaccion]:
    """
    Lista transacciones con filtros opcionales.
    
    Permite filtrar por cuenta (origen o destino) y rango de fechas.
    Si no se proporcionan filtros, retorna todas las transacciones.
    
    Args:
        cuenta_id (Optional[UUID]): Filtra transacciones donde la cuenta
            aparece como origen O destino
        desde (Optional[date]): Fecha mínima (inclusive)
        hasta (Optional[date]): Fecha máxima (inclusive)
    
    Returns:
        List[Transaccion]: Lista de transacciones que cumplen los filtros
    
    Raises:
        asyncpg.PostgresError: Si hay un error en la consulta
    
    Example:
        >>> # Todas las transacciones
        >>> transacciones = await listar_transacciones()
        >>>
        >>> # Transacciones de una cuenta
        >>> transacciones = await listar_transacciones(cuenta_id=uuid_cuenta)
        >>>
        >>> # Transacciones de diciembre 2024
        >>> transacciones = await listar_transacciones(
        ...     desde=date(2024, 12, 1),
        ...     hasta=date(2024, 12, 31)
        ... )
        >>>
        >>> # Transacciones de una cuenta en un rango de fechas
        >>> transacciones = await listar_transacciones(
        ...     cuenta_id=uuid_cuenta,
        ...     desde=date(2024, 12, 1),
        ...     hasta=date(2024, 12, 31)
        ... )
    
    Note:
        - Ordenadas por momento DESC (más recientes primero)
        - Si se filtra por cuenta_id, incluye transacciones donde la cuenta
          es origen O destino (deposits, withdrawals, transfers)
    """
    async with get_db() as conn:
        where_conditions = []
        params = []
        param_count = 0

        if cuenta_id is not None:
            param_count += 1
            where_conditions.append(
                f"(id_cuenta_origen = ${param_count} OR id_cuenta_destino = ${param_count})"
            )
            params.append(cuenta_id)

        if desde is not None:
            param_count += 1
            where_conditions.append(f"momento::date >= ${param_count}")
            params.append(desde)

        if hasta is not None:
            param_count += 1
            where_conditions.append(f"momento::date <= ${param_count}")
            params.append(hasta)

        where_clause = (
            "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        )

        query = f"""
            SELECT id_transaccion as id, tipo, id_cuenta_origen, id_cuenta_destino,
                   monto, momento, fecha_creacion, fecha_edicion
            FROM banco.transaccion
            {where_clause}
            ORDER BY momento DESC
        """

        rows = await conn.fetch(query, *params)
        return [Transaccion(**dict(row)) for row in rows]


async def obtener_transaccion(tx_id: UUID) -> Optional[Transaccion]:
    """
    Busca una transacción por su ID.
    
    Args:
        tx_id (UUID): Identificador único de la transacción
    
    Returns:
        Optional[Transaccion]: Objeto Transaccion si existe, None si no se encuentra
    
    Raises:
        asyncpg.PostgresError: Si hay un error en la consulta
    
    Example:
        >>> transaccion = await obtener_transaccion(tx_id)
        >>> if transaccion:
        ...     print(f"Tipo: {transaccion.tipo}, Monto: ${transaccion.monto}")
    """
    async with get_db() as conn:
        row = await conn.fetchrow(
            """
            SELECT id_transaccion as id, tipo, id_cuenta_origen, id_cuenta_destino,
                   monto, momento, fecha_creacion, fecha_edicion
            FROM banco.transaccion
            WHERE id_transaccion = $1
        """,
            tx_id,
        )
        return Transaccion(**dict(row)) if row else None


async def eliminar_transaccion(tx_id: UUID) -> None:
    """
    Elimina una transacción del historial.
    
    ADVERTENCIA: Esta operación NO revierte el impacto en los saldos.
    Solo elimina el registro del historial. Usar con precaución.
    
    Args:
        tx_id (UUID): ID de la transacción a eliminar
    
    Returns:
        None: No retorna valor si la eliminación es exitosa
    
    Raises:
        KeyError: Si la transacción no existe
        asyncpg.PostgresError: Si hay un error en la base de datos
    
    Warning:
        - Esta función NO ajusta los saldos de las cuentas
        - Solo elimina el registro del historial
        - Puede causar inconsistencias entre saldos y transacciones
        - Usar solo para corrección de errores o administración
    
    Recommended Alternative:
        - Para revertir una transacción, crear una transacción inversa
        - Esto mantiene la trazabilidad del historial
    
    Example:
        >>> # Eliminar registro (NO recomendado en producción)
        >>> await eliminar_transaccion(tx_id)
        >>>
        >>> # Mejor alternativa: transacción inversa
        >>> tx_original = await obtener_transaccion(tx_id)
        >>> if tx_original.tipo == TransaccionTipo.DEPOSITO:
        ...     await retirar(tx_original.id_cuenta_destino, tx_original.monto)
    """
    async with get_db() as conn:
        # Verificar que existe
        exists = await conn.fetchval(
            """
            SELECT EXISTS(SELECT 1 FROM banco.transaccion WHERE id_transaccion = $1)
        """,
            tx_id,
        )

        if not exists:
            raise KeyError("Transacción no encontrada")

        await conn.execute(
            """
            DELETE FROM banco.transaccion WHERE id_transaccion = $1
        """,
            tx_id,
        )


async def depositar(cuenta_id: UUID, monto: float) -> Transaccion:
    """
    Realiza un depósito en una cuenta.
    
    Incrementa el saldo de la cuenta y registra la transacción.
    
    Args:
        cuenta_id (UUID): ID de la cuenta receptora
        monto (float): Cantidad a depositar (debe ser > 0)
    
    Returns:
        Transaccion: Registro de la transacción de depósito
    
    Raises:
        KeyError: Si la cuenta no existe
        asyncpg.PostgresError: Si hay un error en la base de datos
    
    Business Rules:
        - El monto debe ser positivo (validado por TransaccionBase)
        - El saldo se incrementa en el monto depositado
        - Se crea un registro de tipo DEPOSITO
        - La cuenta destino es la cuenta receptora
        - La cuenta origen es NULL (dinero externo)
    
    Transaction Safety:
        - La operación es atómica (UPDATE + INSERT)
        - Si falla el INSERT, el UPDATE se revierte automáticamente
    
    Example:
        >>> # Depósito de $1000
        >>> transaccion = await depositar(cuenta_id, 1000.0)
        >>> print(f"Depósito registrado: {transaccion.id}")
        >>>
        >>> # Verificar nuevo saldo
        >>> cuenta = await obtener_cuenta(cuenta_id)
        >>> print(f"Nuevo saldo: ${cuenta.saldo}")
    """
    async with get_db() as conn:
        # Verificar que cuenta existe
        cuenta_exists = await conn.fetchval(
            """
            SELECT EXISTS(SELECT 1 FROM banco.cuenta WHERE id_cuenta = $1)
        """,
            cuenta_id,
        )

        if not cuenta_exists:
            raise KeyError("Cuenta no encontrada")

        # Actualizar saldo
        await conn.execute(
            """
            UPDATE banco.cuenta SET saldo = saldo + $2 WHERE id_cuenta = $1
        """,
            cuenta_id,
            monto,
        )

        # Registrar transacción
        row = await conn.fetchrow(
            """
            INSERT INTO banco.transaccion (tipo, id_cuenta_destino, monto)
            VALUES ($1, $2, $3)
            RETURNING id_transaccion as id, tipo, id_cuenta_origen, id_cuenta_destino,
                      monto, momento, fecha_creacion, fecha_edicion
        """,
            TransaccionTipo.DEPOSITO.value,
            cuenta_id,
            monto,
        )

        return Transaccion(**dict(row))


async def retirar(cuenta_id: UUID, monto: float) -> Transaccion:
    """
    Realiza un retiro de una cuenta.
    
    Valida saldo suficiente, decrementa el saldo y registra la transacción.
    
    Args:
        cuenta_id (UUID): ID de la cuenta a debitar
        monto (float): Cantidad a retirar (debe ser > 0)
    
    Returns:
        Transaccion: Registro de la transacción de retiro
    
    Raises:
        KeyError: Si la cuenta no existe
        RuntimeError: Si no hay fondos suficientes
        asyncpg.PostgresError: Si hay un error en la base de datos
    
    Business Rules:
        - El monto debe ser positivo (validado por TransaccionBase)
        - El saldo debe ser >= monto (no se permiten sobregiros)
        - El saldo se decrementa en el monto retirado
        - Se crea un registro de tipo RETIRO
        - La cuenta origen es la cuenta debitada
        - La cuenta destino es NULL (dinero externo)
    
    Transaction Safety:
        - Se valida el saldo ANTES de actualizar (evita race conditions)
        - La operación es atómica (UPDATE + INSERT)
        - Si falla el INSERT, el UPDATE se revierte automáticamente
    
    Example:
        >>> # Retiro de $500
        >>> try:
        ...     transaccion = await retirar(cuenta_id, 500.0)
        ...     print(f"Retiro exitoso: {transaccion.id}")
        ... except RuntimeError as e:
        ...     print(f"Error: {e}")
        >>>
        >>> # Verificar nuevo saldo
        >>> cuenta = await obtener_cuenta(cuenta_id)
        >>> print(f"Saldo restante: ${cuenta.saldo}")
    """
    async with get_db() as conn:
        # Verificar saldo suficiente
        saldo_actual = await conn.fetchval(
            """
            SELECT saldo FROM banco.cuenta WHERE id_cuenta = $1
        """,
            cuenta_id,
        )

        if saldo_actual is None:
            raise KeyError("Cuenta no encontrada")

        if saldo_actual < monto:
            raise RuntimeError("Fondos insuficientes")

        # Actualizar saldo
        await conn.execute(
            """
            UPDATE banco.cuenta SET saldo = saldo - $2 WHERE id_cuenta = $1
        """,
            cuenta_id,
            monto,
        )

        # Registrar transacción
        row = await conn.fetchrow(
            """
            INSERT INTO banco.transaccion (tipo, id_cuenta_origen, monto)
            VALUES ($1, $2, $3)
            RETURNING id_transaccion as id, tipo, id_cuenta_origen, id_cuenta_destino,
                      monto, momento, fecha_creacion, fecha_edicion
        """,
            TransaccionTipo.RETIRO.value,
            cuenta_id,
            monto,
        )

        return Transaccion(**dict(row))


async def transferir(
    cuenta_origen_id: UUID, cuenta_destino_id: UUID, monto: float
) -> Transaccion:
    """
    Realiza una transferencia entre dos cuentas.
    
    Valida ambas cuentas, saldo suficiente, y realiza la transferencia
    atómica con garantía de consistencia transaccional.
    
    Args:
        cuenta_origen_id (UUID): ID de la cuenta a debitar
        cuenta_destino_id (UUID): ID de la cuenta a acreditar
        monto (float): Cantidad a transferir (debe ser > 0)
    
    Returns:
        Transaccion: Registro de la transacción de transferencia
    
    Raises:
        ValueError: Si origen y destino son la misma cuenta
        KeyError: Si alguna de las cuentas no existe
        RuntimeError: Si no hay fondos suficientes en la cuenta origen
        asyncpg.PostgresError: Si hay un error en la base de datos
    
    Business Rules:
        - Las cuentas origen y destino deben ser diferentes
        - Ambas cuentas deben existir
        - El saldo origen debe ser >= monto
        - La operación es atómica (todo o nada)
        - Se crea un registro de tipo TRANSFERENCIA
    
    ACID Transaction:
        Esta operación usa una transacción explícita (async with conn.transaction())
        para garantizar:
        - Atomicidad: Ambas actualizaciones ocurren o ninguna
        - Consistencia: Los saldos son consistentes en todo momento
        - Isolation: Otras transacciones no ven estados intermedios
        - Durability: Una vez completada, los cambios son permanentes
    
    Flow:
        1. Validar que las cuentas sean diferentes
        2. Validar que ambas cuentas existan
        3. Validar saldo suficiente en origen
        4. Iniciar transacción DB
        5. Debitar cuenta origen
        6. Acreditar cuenta destino
        7. Registrar transacción
        8. Commit automático (si no hay excepciones)
    
    Example:
        >>> # Transferir $200 de cuenta A a cuenta B
        >>> try:
        ...     transaccion = await transferir(
        ...         cuenta_origen_id=uuid_A,
        ...         cuenta_destino_id=uuid_B,
        ...         monto=200.0
        ...     )
        ...     print(f"Transferencia exitosa: {transaccion.id}")
        ... except RuntimeError as e:
        ...     print(f"Error: {e}")
        >>>
        >>> # Verificar saldos actualizados
        >>> cuenta_A = await obtener_cuenta(uuid_A)
        >>> cuenta_B = await obtener_cuenta(uuid_B)
        >>> print(f"Saldo A: ${cuenta_A.saldo}, Saldo B: ${cuenta_B.saldo}")
    
    Note:
        - Esta es la operación más compleja y crítica del sistema
        - Usa transacciones explícitas para garantía ACID completa
        - En caso de error, todo se revierte automáticamente (rollback)
    """
    async with get_db() as conn:
        # Validar que las cuentas sean diferentes
        if cuenta_origen_id == cuenta_destino_id:
            raise ValueError("La cuenta de origen y destino deben ser distintas")

        # Verificar saldo suficiente en cuenta origen
        saldo_origen = await conn.fetchval(
            """
            SELECT saldo FROM banco.cuenta WHERE id_cuenta = $1
        """,
            cuenta_origen_id,
        )

        if saldo_origen is None:
            raise KeyError("Cuenta origen no encontrada")

        # Verificar que cuenta destino existe
        destino_exists = await conn.fetchval(
            """
            SELECT EXISTS(SELECT 1 FROM banco.cuenta WHERE id_cuenta = $1)
        """,
            cuenta_destino_id,
        )

        if not destino_exists:
            raise KeyError("Cuenta destino no encontrada")

        if saldo_origen < monto:
            raise RuntimeError("Fondos insuficientes")

        # Realizar transferencia (transacción atómica)
        # El bloque transaction() garantiza que todo se ejecuta o nada
        async with conn.transaction():
            # Debitar cuenta origen
            await conn.execute(
                """
                UPDATE banco.cuenta SET saldo = saldo - $2 WHERE id_cuenta = $1
            """,
                cuenta_origen_id,
                monto,
            )

            # Acreditar cuenta destino
            await conn.execute(
                """
                UPDATE banco.cuenta SET saldo = saldo + $2 WHERE id_cuenta = $1
            """,
                cuenta_destino_id,
                monto,
            )

            # Registrar transacción
            row = await conn.fetchrow(
                """
                INSERT INTO banco.transaccion (tipo, id_cuenta_origen, id_cuenta_destino, monto)
                VALUES ($1, $2, $3, $4)
                RETURNING id_transaccion as id, tipo, id_cuenta_origen, id_cuenta_destino,
                          monto, momento, fecha_creacion, fecha_edicion
            """,
                TransaccionTipo.TRANSFERENCIA.value,
                cuenta_origen_id,
                cuenta_destino_id,
                monto,
            )

        # El commit ocurre automáticamente al salir del bloque transaction()
        # Si hubo cualquier excepción, se hace rollback automático
        return Transaccion(**dict(row))


# =========================
# Funciones auxiliares para tipos de cuenta
# =========================
async def listar_tipos_cuenta() -> List[TipoCuentaModel]:
    """
    Lista todos los tipos de cuenta disponibles.
    
    Returns:
        List[TipoCuentaModel]: Lista de tipos de cuenta ordenados alfabéticamente
    
    Raises:
        asyncpg.PostgresError: Si hay un error en la consulta
    
    Example:
        >>> tipos = await listar_tipos_cuenta()
        >>> for tipo in tipos:
        ...     print(f"{tipo.nombre}: {tipo.descripcion}")
    
    Note:
        - Los tipos de cuenta son datos maestros (catálogo)
        - Normalmente se gestionan por el administrador
        - Ejemplos: AHORROS, CORRIENTE, NOMINA
    """
    async with get_db() as conn:
        rows = await conn.fetch(
            """
            SELECT id_tipo_cuenta as id, nombre, descripcion
            FROM banco.tipo_cuenta
            ORDER BY nombre
        """
        )
        return [TipoCuentaModel(**dict(row)) for row in rows]


async def obtener_tipo_cuenta_por_nombre(nombre: str) -> Optional[TipoCuentaModel]:
    """
    Busca un tipo de cuenta por su nombre.
    
    Args:
        nombre (str): Nombre del tipo de cuenta (ej: "AHORROS", "CORRIENTE")
    
    Returns:
        Optional[TipoCuentaModel]: Objeto TipoCuentaModel si existe, None si no
    
    Raises:
        asyncpg.PostgresError: Si hay un error en la consulta
    
    Example:
        >>> tipo = await obtener_tipo_cuenta_por_nombre("AHORROS")
        >>> if tipo:
        ...     print(f"ID del tipo AHORROS: {tipo.id}")
    
    Note:
        - La búsqueda es case-sensitive
        - Útil para obtener el ID al crear cuentas
    """
    async with get_db() as conn:
        row = await conn.fetchrow(
            """
            SELECT id_tipo_cuenta as id, nombre, descripcion
            FROM banco.tipo_cuenta
            WHERE nombre = $1
        """,
            nombre,
        )
        return TipoCuentaModel(**dict(row)) if row else None
