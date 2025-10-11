# init_db.py
# Script para inicializar datos básicos en la base de datos

import asyncio
import os
from dotenv import load_dotenv
import asyncpg

# Cargar variables de entorno
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

async def init_database():
    """Inicializa los datos básicos en la base de datos"""
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        # Verificar si ya existe el esquema banco
        schema_exists = await conn.fetchval("""
            SELECT EXISTS(SELECT 1 FROM information_schema.schemata WHERE schema_name = 'banco')
        """)
        
        if not schema_exists:
            # Crear esquema banco
            await conn.execute("CREATE SCHEMA banco;")
            print("✅ Esquema 'banco' creado")
        
        # Crear extensión UUID si no existe
        await conn.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')
        print("✅ Extensión UUID creada")
        
        # Ejecutar el script SQL para crear las tablas
        sql_script = """
        -- 1) Usuario sistema (UUID fijo)
        DROP TABLE IF EXISTS banco.usuario CASCADE;
        CREATE TABLE banco.usuario (
            id_usuario           UUID PRIMARY KEY DEFAULT uuid_generate_v1(),
            primer_nombre        VARCHAR(50),
            segundo_nombre       VARCHAR(50),
            primer_apellido      VARCHAR(50),
            segundo_apellido     VARCHAR(50),
            correo               VARCHAR(120) UNIQUE,
            hash_password        TEXT NOT NULL,
            rol                  VARCHAR(30),
            fecha_nacimiento     DATE,
            id_usuario_creacion  UUID,
            id_usuario_edicion   UUID,
            fecha_creacion       TIMESTAMPTZ NOT NULL DEFAULT now(),
            fecha_edicion        TIMESTAMPTZ
        );
        
        -- Insertar usuario sistema
        INSERT INTO banco.usuario (
            id_usuario, primer_nombre, primer_apellido, correo, hash_password, rol,
            id_usuario_creacion, fecha_creacion
        ) VALUES (
            '00000000-0000-0000-0000-000000000001', 'SYSTEM','USER','system@local','*','system',
            '00000000-0000-0000-0000-000000000001', now()
        );
        
        -- Agregar FKs de auditoría
        ALTER TABLE banco.usuario
            ALTER COLUMN id_usuario_creacion SET DEFAULT '00000000-0000-0000-0000-000000000001'::uuid;
        ALTER TABLE banco.usuario
            ALTER COLUMN id_usuario_creacion SET NOT NULL;
        ALTER TABLE banco.usuario
            ADD CONSTRAINT fk_usuario_creacion FOREIGN KEY (id_usuario_creacion) REFERENCES banco.usuario(id_usuario);
        ALTER TABLE banco.usuario
            ADD CONSTRAINT fk_usuario_edicion  FOREIGN KEY (id_usuario_edicion)  REFERENCES banco.usuario(id_usuario);
        
        -- 2) CLIENTE
        DROP TABLE IF EXISTS banco.cliente CASCADE;
        CREATE TABLE banco.cliente (
            id_cliente           UUID PRIMARY KEY DEFAULT uuid_generate_v1(),
            nombre_completo      VARCHAR(120) NOT NULL,
            documento            VARCHAR(40) UNIQUE NOT NULL,
            id_usuario_creacion  UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000001',
            id_usuario_edicion   UUID,
            fecha_creacion       TIMESTAMPTZ NOT NULL DEFAULT now(),
            fecha_edicion        TIMESTAMPTZ,
            CONSTRAINT fk_cliente_creacion FOREIGN KEY (id_usuario_creacion) REFERENCES banco.usuario(id_usuario),
            CONSTRAINT fk_cliente_edicion  FOREIGN KEY (id_usuario_edicion)  REFERENCES banco.usuario(id_usuario)
        );
        
        -- 3) TIPO_CUENTA
        DROP TABLE IF EXISTS banco.tipo_cuenta CASCADE;
        CREATE TABLE banco.tipo_cuenta (
            id_tipo_cuenta       UUID PRIMARY KEY DEFAULT uuid_generate_v1(),
            nombre               VARCHAR(30) UNIQUE NOT NULL,
            descripcion          VARCHAR(200),
            id_usuario_creacion  UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000001',
            id_usuario_edicion   UUID,
            fecha_creacion       TIMESTAMPTZ NOT NULL DEFAULT now(),
            fecha_edicion        TIMESTAMPTZ,
            CONSTRAINT fk_tipo_cuenta_creacion FOREIGN KEY (id_usuario_creacion) REFERENCES banco.usuario(id_usuario),
            CONSTRAINT fk_tipo_cuenta_edicion  FOREIGN KEY (id_usuario_edicion)  REFERENCES banco.usuario(id_usuario)
        );
        
        -- 4) CUENTA
        DROP TABLE IF EXISTS banco.cuenta CASCADE;
        CREATE TABLE banco.cuenta (
            id_cuenta            UUID PRIMARY KEY DEFAULT uuid_generate_v1(),
            numero               VARCHAR(30) UNIQUE NOT NULL,
            id_cliente           UUID NOT NULL,
            id_tipo_cuenta       UUID NOT NULL,
            saldo                NUMERIC(18,2) NOT NULL DEFAULT 0,
            id_usuario_creacion  UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000001',
            id_usuario_edicion   UUID,
            fecha_creacion       TIMESTAMPTZ NOT NULL DEFAULT now(),
            fecha_edicion        TIMESTAMPTZ,
            CONSTRAINT fk_cuenta_cliente     FOREIGN KEY (id_cliente) REFERENCES banco.cliente(id_cliente),
            CONSTRAINT fk_cuenta_tipo_cuenta FOREIGN KEY (id_tipo_cuenta) REFERENCES banco.tipo_cuenta(id_tipo_cuenta),
            CONSTRAINT fk_cuenta_creacion    FOREIGN KEY (id_usuario_creacion) REFERENCES banco.usuario(id_usuario),
            CONSTRAINT fk_cuenta_edicion     FOREIGN KEY (id_usuario_edicion)  REFERENCES banco.usuario(id_usuario)
        );
        CREATE INDEX ix_cuenta_cliente ON banco.cuenta(id_cliente);
        
        -- 5) TRANSACCION
        DROP TABLE IF EXISTS banco.transaccion CASCADE;
        CREATE TABLE banco.transaccion (
            id_transaccion       UUID PRIMARY KEY DEFAULT uuid_generate_v1(),
            id_cuenta_origen     UUID,
            id_cuenta_destino    UUID,
            tipo                 VARCHAR(20) NOT NULL CHECK (tipo IN ('DEPOSITO','RETIRO','TRANSFERENCIA')),
            monto                NUMERIC(18,2) NOT NULL CHECK (monto > 0),
            momento              TIMESTAMPTZ NOT NULL DEFAULT now(),
            id_usuario_creacion  UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000001',
            id_usuario_edicion   UUID,
            fecha_creacion       TIMESTAMPTZ NOT NULL DEFAULT now(),
            fecha_edicion        TIMESTAMPTZ,
            CONSTRAINT fk_tx_origen   FOREIGN KEY (id_cuenta_origen)  REFERENCES banco.cuenta(id_cuenta),
            CONSTRAINT fk_tx_destino  FOREIGN KEY (id_cuenta_destino) REFERENCES banco.cuenta(id_cuenta),
            CONSTRAINT fk_tx_creacion FOREIGN KEY (id_usuario_creacion) REFERENCES banco.usuario(id_usuario),
            CONSTRAINT fk_tx_edicion  FOREIGN KEY (id_usuario_edicion)  REFERENCES banco.usuario(id_usuario)
        );
        CREATE INDEX ix_tx_origen  ON banco.transaccion(id_cuenta_origen);
        CREATE INDEX ix_tx_destino ON banco.transaccion(id_cuenta_destino);
        CREATE INDEX ix_tx_tipo    ON banco.transaccion(tipo);
        
        -- 6) Insertar tipos de cuenta básicos
        INSERT INTO banco.tipo_cuenta (nombre, descripcion)
            VALUES ('AHORROS','Cuenta de ahorros')
            ON CONFLICT (nombre) DO NOTHING;
        
        INSERT INTO banco.tipo_cuenta (nombre, descripcion)
            VALUES ('CORRIENTE','Cuenta corriente')
            ON CONFLICT (nombre) DO NOTHING;
        """
        
        await conn.execute(sql_script)
        print("✅ Tablas creadas exitosamente")
        print("✅ Tipos de cuenta básicos insertados")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    print("🚀 Inicializando base de datos...")
    asyncio.run(init_database())
    print("✅ Base de datos inicializada correctamente")