"""
Módulo de Extracción y Diagnóstico de Calidad Inicial (Fase 1)
Carga datos crudos y genera métricas objetivas de completitud, unicidad y dtypes.
"""
import json
import pandas as pd
from typing import Tuple, Dict, Any
from pathlib import Path
from src.config import DATASET_CATALOGO, DATASET_FISICA, DATASET_ONLINE

def cargar_catalogo(path_catalogo: Path = DATASET_CATALOGO) -> pd.DataFrame:
    """Carga el catálogo maestro de productos asegurando tipos de datos base."""
    df = pd.read_csv(path_catalogo, encoding='utf-8')
    df['id_producto'] = df['id_producto'].astype(str).str.strip()
    return df

def cargar_ventas_fisicas(path_fisica: Path = DATASET_FISICA) -> pd.DataFrame:
    """Carga las ventas de tienda física en crudo."""
    df = pd.read_csv(path_fisica, encoding='utf-8')
    return df

def cargar_ventas_online(path_online: Path = DATASET_ONLINE) -> pd.DataFrame:
    """Carga las ventas web / e-commerce en crudo desde archivo JSON."""
    with open(path_online, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return pd.DataFrame(data)

def perfilar_dataset(df: pd.DataFrame, nombre: str) -> Dict[str, Any]:
    """
    Ejecuta el diagnóstico cuantitativo de calidad de datos (Fase 1).
    Calcula completitud (% nulos), unicidad (duplicados exactos) y tipos inferidos.
    """
    total_filas = len(df)
    nulos_por_columna = df.isnull().sum().to_dict()
    pct_nulos = {col: round((nulos / total_filas) * 100, 2) for col, nulos in nulos_por_columna.items()}
    duplicados_exactos = int(df.duplicated().sum())
    unicidad_pct = round(((total_filas - duplicados_exactos) / total_filas) * 100, 2) if total_filas > 0 else 0.0
    dtypes_map = {col: str(dtype) for col, dtype in df.dtypes.items()}

    return {
        "nombre_dataset": nombre,
        "total_registros": total_filas,
        "total_columnas": len(df.columns),
        "duplicados_exactos": duplicados_exactos,
        "porcentaje_unicidad": unicidad_pct,
        "conteo_nulos": nulos_por_columna,
        "porcentaje_nulos": pct_nulos,
        "tipos_de_datos": dtypes_map
    }

def ejecutar_diagnostico_inicial() -> Dict[str, Any]:
    """Carga todos los datos crudos y compila el reporte de diagnóstico de calidad inicial."""
    cat = cargar_catalogo()
    fis = cargar_ventas_fisicas()
    onl = cargar_ventas_online()

    reporte = {
        "catalogo": perfilar_dataset(cat, "Catálogo de Productos"),
        "tienda_fisica": perfilar_dataset(fis, "Ventas Tienda Física"),
        "tienda_online": perfilar_dataset(onl, "Ventas Tienda Web Online")
    }
    return reporte
