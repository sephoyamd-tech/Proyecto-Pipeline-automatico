"""
Módulo de Configuración Centralizada del Pipeline ETL
Grupo 1 (LCS2) - Retail & E-commerce Omnicanal
"""
from pathlib import Path

# Rutas del Proyecto
BASE_DIR = Path(__file__).resolve().parent.parent
DATASET_CATALOGO = BASE_DIR / "catalogo_productos.csv"
DATASET_FISICA = BASE_DIR / "ventas_tienda_fisica.csv"
DATASET_ONLINE = BASE_DIR / "ventas_online.json"
DATABASE_PATH = BASE_DIR / "retail_omnicanal.db"

# Parámetros Financieros y de Negocio
TIPO_CAMBIO_USD_MXN = 19.50  # Paridad oficial especificada en los lineamientos
IQR_FACTOR = 1.5              # Factor estándar de Tukey para Rango Intercuartílico

# Constantes de Imputación (MCAR / MAR)
VALOR_IMPUTACION_CLIENTE = "ANONIMO"
VALOR_IMPUTACION_DIRECCION = "SIN_DIRECCION"

# Categorías de Discretización
DISCRETIZACION_LABELS = ["Bajo", "Medio", "Alto"]

# Motivos Estandarizados de Cuarentena
MOTIVO_DUPLICADO = "DUPLICADO_EXACTO_POS"
MOTIVO_CANTIDAD_INVALIDA = "VALOR_IMPOSIBLE_CANTIDAD_NO_POSITIVA"
MOTIVO_PRODUCTO_HUERFANO = "PRODUCTO_HUERFANO_NO_CATALOGADO"
MOTIVO_CORREO_INVALIDO = "CORREO_ELECTRONICO_INVALIDO"
MOTIVO_PYDANTIC_FALLO = "ERROR_VALIDACION_ESQUEMA_PYDANTIC"
