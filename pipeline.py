"""
=============================================================================
PIPELINE ETL ROBUSTO CON ZONA DE CUARENTENA - END-TO-END
Materia: Ingeniería de Datos (ATD-2602) | Unidad 2: Limpieza y Preprocesamiento
Sector: Retail & E-commerce Omnicanal (Grupo 1 - LCS2)
=============================================================================
"""
import sys
import json
import logging
from datetime import datetime
from pathlib import Path

# Configuración de logging profesional
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("ETL_Omnicanal")

from src.config import DATABASE_PATH
from src.extract import (
    cargar_catalogo,
    cargar_ventas_fisicas,
    cargar_ventas_online,
    ejecutar_diagnostico_inicial
)
from src.transform import (
    transformar_ventas_fisicas,
    transformar_ventas_online,
    aplicar_capping_iqr_cantidades,
    aplicar_escalamiento_y_discretizacion
)
from src.quarantine import segregar_con_pydantic
from src.load import (
    inicializar_base_de_datos,
    persistir_catalogo,
    persistir_transacciones_limpias,
    persistir_cuarentena,
    obtener_metricas_base_datos
)

def ejecutar_pipeline() -> dict:
    inicio_pipeline = datetime.now()
    logger.info("=" * 70)
    logger.info("INICIANDO EJECUCIÓN DEL PIPELINE ETL OMNICANAL (GRUPO 1 - LCS2)")
    logger.info("=" * 70)

    # -------------------------------------------------------------------------
    # FASE 1: DIAGNÓSTICO DE CALIDAD INICIAL
    # -------------------------------------------------------------------------
    logger.info(">>> FASE 1: Ejecutando perfilado cuantitativo de datos crudos...")
    diagnostico_inicial = ejecutar_diagnostico_inicial()
    logger.info("Métricas de datos crudos ingeridos:")
    logger.info(f" - Catálogo: {diagnostico_inicial['catalogo']['total_registros']} registros.")
    logger.info(f" - Ventas Físicas: {diagnostico_inicial['tienda_fisica']['total_registros']} registros, "
                f"duplicados: {diagnostico_inicial['tienda_fisica']['duplicados_exactos']}.")
    logger.info(f" - Ventas Online: {diagnostico_inicial['tienda_online']['total_registros']} registros, "
                f"nulos en email: {diagnostico_inicial['tienda_online']['conteo_nulos'].get('customer_email')}.")

    # Carga de dataframes en memoria
    df_cat = cargar_catalogo()
    df_fis = cargar_ventas_fisicas()
    df_onl = cargar_ventas_online()

    cat_dict = df_cat.set_index('id_producto').to_dict(orient='index')

    # -------------------------------------------------------------------------
    # FASE 2, 4: TRANSFORMACIÓN, UNIFICACIÓN, DIVISAS Y HUÉRFANOS
    # -------------------------------------------------------------------------
    logger.info(">>> FASE 2 & 4: Procesando ventas físicas e imputación MCAR...")
    cand_fis, quar_fis = transformar_ventas_fisicas(df_fis, cat_dict)
    logger.info(f" - Físicas válidas iniciales: {len(cand_fis)} | Desviadas a cuarentena: {len(quar_fis)}")

    logger.info(">>> FASE 2 & 4: Procesando ventas online (conversión USD->MXN @ $19.50 y validación email)...")
    cand_onl, quar_onl = transformar_ventas_online(df_onl, cat_dict)
    logger.info(f" - Online válidas iniciales: {len(cand_onl)} | Desviadas a cuarentena: {len(quar_onl)}")

    candidatos_totales = cand_fis + cand_onl
    cuarentena_acumulada = quar_fis + quar_onl

    # -------------------------------------------------------------------------
    # FASE 3: TRATAMIENTO DE OUTLIERS CON IQR (CAPPING / WINSORIZING)
    # -------------------------------------------------------------------------
    logger.info(">>> FASE 3: Calculando IQR y aplicando Capping / Winsorizing en cantidades y montos...")
    candidatos_totales, stats_iqr = aplicar_capping_iqr_cantidades(candidatos_totales)
    logger.info(f" - IQR: {stats_iqr['iqr']} | Umbral Capping: {stats_iqr['limite_capping']} unidades.")
    logger.info(f" - Registros con compras gigantes cappeados: {stats_iqr['registros_cappeados']}")

    # -------------------------------------------------------------------------
    # FASE 5: TRANSFORMACIÓN, DISCRETIZACIÓN Y ESCALAMIENTO
    # -------------------------------------------------------------------------
    logger.info(">>> FASE 5: Aplicando Min-Max [0, 1] y discretización en cuantiles [Bajo, Medio, Alto]...")
    candidatos_totales, stats_escalamiento = aplicar_escalamiento_y_discretizacion(candidatos_totales)
    logger.info(f" - Rango montos: ${stats_escalamiento['min_monto']:,.2f} a ${stats_escalamiento['max_monto']:,.2f}")
    logger.info(f" - Tercil 1 (Bajo/Medio): ${stats_escalamiento['tercil_1']:,.2f} | Tercil 2 (Medio/Alto): ${stats_escalamiento['tercil_2']:,.2f}")

    # -------------------------------------------------------------------------
    # FASE 6: VALIDACIÓN CON PYDANTIC Y BIFURCACIÓN A CUARENTENA
    # -------------------------------------------------------------------------
    logger.info(">>> FASE 6: Validación estricta con esquemas Pydantic y captura de ValidationError...")
    limpias_validadas, cuarentena_final = segregar_con_pydantic(candidatos_totales, cuarentena_acumulada)
    logger.info(f" - Transacciones conformes aprobadas: {len(limpias_validadas)}")
    logger.info(f" - Total registros en Zona de Cuarentena: {len(cuarentena_final)}")

    # -------------------------------------------------------------------------
    # FASE 7: CARGA TRANSACCIONAL A BASE DE DATOS SQLITE
    # -------------------------------------------------------------------------
    logger.info(f">>> FASE 7: Persistiendo datos en SQLite relacional ({DATABASE_PATH})...")
    inicializar_base_de_datos(DATABASE_PATH)
    persistir_catalogo(df_cat, DATABASE_PATH)
    persistir_transacciones_limpias(limpias_validadas, DATABASE_PATH)
    persistir_cuarentena(cuarentena_final, DATABASE_PATH)

    metricas_bd = obtener_metricas_base_datos(DATABASE_PATH)
    tiempo_total = (datetime.now() - inicio_pipeline).total_seconds()

    logger.info("=" * 70)
    logger.info(f"PIPELINE FINALIZADO EXITOSAMENTE EN {tiempo_total:.2f} SEGUNDOS")
    logger.info(f" - Registros Catálogo Maestro en BD: {metricas_bd['catalogo_registros']}")
    logger.info(f" - Transacciones Limpias en BD: {metricas_bd['transacciones_limpias_total']}")
    logger.info(f"   * Físicas: {metricas_bd['transacciones_fisicas_limpias']} | Online: {metricas_bd['transacciones_online_limpias']}")
    logger.info(f" - Registros en Cuarentena Auditables: {metricas_bd['cuarentena_errores_total']}")
    logger.info(f" - Desglose de motivos de rechazo:")
    for motivo, cnt in metricas_bd['desglose_cuarentena'].items():
        logger.info(f"   * {motivo}: {cnt} registros")
    logger.info("=" * 70)

    resultado = {
        "tiempo_ejecucion_segundos": tiempo_total,
        "diagnostico_inicial": diagnostico_inicial,
        "estadisticas_iqr": stats_iqr,
        "estadisticas_escalamiento": stats_escalamiento,
        "metricas_bd": metricas_bd
    }

    # Guardar reporte JSON de ejecución para dashboard web
    with open("reporte_ejecucion.json", "w", encoding="utf-8") as f:
        json.dump(resultado, f, indent=2, ensure_ascii=False)

    return resultado

if __name__ == "__main__":
    ejecutar_pipeline()
