"""
Módulo de Persistencia Transaccional en Base de Datos Relacional (Fase 7)
Maneja conexiones, DDL de tablas y transacciones seguras (commit/rollback) en SQLite.
"""
import sqlite3
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Tuple
from src.config import DATABASE_PATH

DDL_CATALOGO = """
CREATE TABLE IF NOT EXISTS catalogo_productos (
    id_producto TEXT PRIMARY KEY,
    nombre_producto TEXT NOT NULL,
    categoria TEXT NOT NULL,
    precio_base_mxn REAL NOT NULL,
    stock_minimo INTEGER NOT NULL,
    proveedor TEXT NOT NULL
);
"""

DDL_TRANSACCIONES_LIMPIAS = """
CREATE TABLE IF NOT EXISTS transacciones_limpias (
    id_transaccion TEXT PRIMARY KEY,
    fecha DATE NOT NULL,
    canal TEXT NOT NULL,
    sucursal TEXT NOT NULL,
    id_producto TEXT NOT NULL,
    nombre_producto TEXT NOT NULL,
    categoria TEXT NOT NULL,
    proveedor TEXT NOT NULL,
    cantidad INTEGER NOT NULL,
    cantidad_original INTEGER NOT NULL,
    precio_unitario_mxn REAL NOT NULL,
    monto_total_mxn REAL NOT NULL,
    monto_total_original REAL NOT NULL,
    monto_escalado_minmax REAL NOT NULL,
    segmento_monto TEXT NOT NULL,
    id_cliente TEXT NOT NULL,
    cliente_email TEXT,
    direccion_envio TEXT,
    metodo_pago TEXT NOT NULL,
    estado_transaccion TEXT NOT NULL,
    fecha_procesamiento TEXT NOT NULL,
    FOREIGN KEY (id_producto) REFERENCES catalogo_productos(id_producto)
);
"""

DDL_CUARENTENA_ERRORES = """
CREATE TABLE IF NOT EXISTS cuarentena_errores (
    id_registro_cuarentena INTEGER PRIMARY KEY AUTOINCREMENT,
    id_transaccion_origen TEXT NOT NULL,
    fuente_origen TEXT NOT NULL,
    fecha_ingestion TEXT NOT NULL,
    motivo_rechazo_cuarentena TEXT NOT NULL,
    campo_erroneo TEXT NOT NULL,
    valor_invalido TEXT,
    datos_crudos_json TEXT NOT NULL
);
"""

INDICES_SQL = """
CREATE INDEX IF NOT EXISTS idx_trans_fecha ON transacciones_limpias (fecha);
CREATE INDEX IF NOT EXISTS idx_trans_canal ON transacciones_limpias (canal);
CREATE INDEX IF NOT EXISTS idx_trans_producto ON transacciones_limpias (id_producto);
CREATE INDEX IF NOT EXISTS idx_cuarentena_motivo ON cuarentena_errores (motivo_rechazo_cuarentena);
"""

def inicializar_base_de_datos(db_path: Path = DATABASE_PATH) -> None:
    """Crea la estructura de tablas e índices si no existen."""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(DDL_CATALOGO)
        cursor.execute(DDL_TRANSACCIONES_LIMPIAS)
        cursor.execute(DDL_CUARENTENA_ERRORES)
        cursor.executescript(INDICES_SQL)
        conn.commit()


def persistir_catalogo(
    catalogo_df: pd.DataFrame,
    db_path: Path = DATABASE_PATH
) -> int:
    """Inserta o actualiza el catálogo maestro con transacción segura."""
    registros = catalogo_df[[
        'id_producto', 'nombre_producto', 'categoria',
        'precio_base_mxn', 'stock_minimo', 'proveedor'
    ]].to_dict(orient='records')

    sql = """
    INSERT OR REPLACE INTO catalogo_productos (
        id_producto, nombre_producto, categoria,
        precio_base_mxn, stock_minimo, proveedor
    ) VALUES (
        :id_producto, :nombre_producto, :categoria,
        :precio_base_mxn, :stock_minimo, :proveedor
    );
    """
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.executemany(sql, registros)
        conn.commit()
        return len(registros)
    except Exception as e:
        conn.rollback()
        raise RuntimeError(f"Error al persistir catálogo maestro: {str(e)}")
    finally:
        conn.close()


def persistir_transacciones_limpias(
    transacciones: List[Dict[str, Any]],
    db_path: Path = DATABASE_PATH
) -> int:
    """Inserta las transacciones conformes en un bloque transaccional atómico."""
    if not transacciones:
        return 0

    sql = """
    INSERT OR REPLACE INTO transacciones_limpias (
        id_transaccion, fecha, canal, sucursal, id_producto,
        nombre_producto, categoria, proveedor, cantidad, cantidad_original,
        precio_unitario_mxn, monto_total_mxn, monto_total_original,
        monto_escalado_minmax, segmento_monto, id_cliente,
        cliente_email, direccion_envio, metodo_pago,
        estado_transaccion, fecha_procesamiento
    ) VALUES (
        :id_transaccion, :fecha, :canal, :sucursal, :id_producto,
        :nombre_producto, :categoria, :proveedor, :cantidad, :cantidad_original,
        :precio_unitario_mxn, :monto_total_mxn, :monto_total_original,
        :monto_escalado_minmax, :segmento_monto, :id_cliente,
        :cliente_email, :direccion_envio, :metodo_pago,
        :estado_transaccion, :fecha_procesamiento
    );
    """
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.executemany(sql, transacciones)
        conn.commit()
        return len(transacciones)
    except Exception as e:
        conn.rollback()
        raise RuntimeError(f"Falla transaccional en carga de transacciones limpias: {str(e)}")
    finally:
        conn.close()


def persistir_cuarentena(
    cuarentena_lista: List[Dict[str, Any]],
    db_path: Path = DATABASE_PATH
) -> int:
    """Inserta los registros anómalos en la tabla cuarentena_errores."""
    if not cuarentena_lista:
        return 0

    sql = """
    INSERT INTO cuarentena_errores (
        id_transaccion_origen, fuente_origen, fecha_ingestion,
        motivo_rechazo_cuarentena, campo_erroneo, valor_invalido, datos_crudos_json
    ) VALUES (
        :id_transaccion_origen, :fuente_origen, :fecha_ingestion,
        :motivo_rechazo_cuarentena, :campo_erroneo, :valor_invalido, :datos_crudos_json
    );
    """
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.executemany(sql, cuarentena_lista)
        conn.commit()
        return len(cuarentena_lista)
    except Exception as e:
        conn.rollback()
        raise RuntimeError(f"Falla transaccional en persistencia de cuarentena: {str(e)}")
    finally:
        conn.close()


def obtener_metricas_base_datos(db_path: Path = DATABASE_PATH) -> Dict[str, Any]:
    """Consulta la base de datos para auditar los registros cargados."""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM catalogo_productos;")
        total_catalogo = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM transacciones_limpias;")
        total_limpias = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM transacciones_limpias WHERE canal = 'FISICO';")
        total_fisicas = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM transacciones_limpias WHERE canal = 'ONLINE';")
        total_online = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM cuarentena_errores;")
        total_cuarentena = cursor.fetchone()[0]

        cursor.execute("""
            SELECT motivo_rechazo_cuarentena, COUNT(*)
            FROM cuarentena_errores
            GROUP BY motivo_rechazo_cuarentena
            ORDER BY COUNT(*) DESC;
        """)
        desglose_cuarentena = dict(cursor.fetchall())

    return {
        "catalogo_registros": total_catalogo,
        "transacciones_limpias_total": total_limpias,
        "transacciones_fisicas_limpias": total_fisicas,
        "transacciones_online_limpias": total_online,
        "cuarentena_errores_total": total_cuarentena,
        "desglose_cuarentena": desglose_cuarentena
    }
