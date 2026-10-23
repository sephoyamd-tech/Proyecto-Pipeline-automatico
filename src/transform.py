"""
Módulo de Transformación, Imputación, Outliers, Fusión y Escalamiento (Fases 2, 3, 4, 5)
Implementa el preprocesamiento estadístico riguroso y segregación a cuarentena.
"""
import re
import json
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Tuple, List, Dict, Any, Optional

from src.config import (
    TIPO_CAMBIO_USD_MXN,
    IQR_FACTOR,
    VALOR_IMPUTACION_CLIENTE,
    VALOR_IMPUTACION_DIRECCION,
    DISCRETIZACION_LABELS,
    MOTIVO_DUPLICADO,
    MOTIVO_CANTIDAD_INVALIDA,
    MOTIVO_PRODUCTO_HUERFANO,
    MOTIVO_CORREO_INVALIDO
)

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')

def normalizar_fecha(val: Any) -> str:
    """
    Homologa cualquier formato de fecha (DD-MM-YYYY, DD/MM/YYYY, ISO string o Unix timestamp)
    al estándar ISO YYYY-MM-DD.
    """
    if val is None or pd.isna(val):
        raise ValueError("Fecha nula o vacía")

    # Si es un número entero/flotante (Unix Epoch Timestamp)
    if isinstance(val, (int, float)) and not isinstance(val, bool):
        dt = datetime.fromtimestamp(float(val))
        return dt.strftime('%Y-%m-%d')

    s = str(val).strip()

    # Si es un string con timestamp numérico
    if s.isdigit():
        dt = datetime.fromtimestamp(float(s))
        return dt.strftime('%Y-%m-%d')

    # Si incluye hora con 'T' o espacio (ej. 2026-10-02T15:27:00)
    if 'T' in s:
        s = s.split('T')[0]
    elif ' ' in s:
        s = s.split(' ')[0]

    # Patrón YYYY-MM-DD
    if re.match(r'^\d{4}-\d{2}-\d{2}$', s):
        datetime.strptime(s, '%Y-%m-%d')
        return s

    # Patrón DD-MM-YYYY
    if re.match(r'^\d{2}-\d{2}-\d{4}$', s):
        dt = datetime.strptime(s, '%d-%m-%Y')
        return dt.strftime('%Y-%m-%d')

    # Patrón DD/MM/YYYY
    if re.match(r'^\d{2}/\d{2}/\d{4}$', s):
        dt = datetime.strptime(s, '%d/%m/%Y')
        return dt.strftime('%Y-%m-%d')

    # Patrón YYYY/MM/DD
    if re.match(r'^\d{4}/\d{2}/\d{2}$', s):
        dt = datetime.strptime(s, '%Y/%m/%d')
        return dt.strftime('%Y-%m-%d')

    # Intentar parseo genérico con pandas
    parsed = pd.to_datetime(s, dayfirst=True)
    return parsed.strftime('%Y-%m-%d')


def homologar_metodo_pago(metodo: str) -> str:
    """Estandariza los métodos de pago a categorías limpias."""
    if not metodo or pd.isna(metodo):
        return "OTRO"
    m = str(metodo).strip().upper()
    if "EFECTIVO" in m:
        return "EFECTIVO"
    elif "CRÉDITO" in m or "CREDITO" in m:
        return "TARJETA_CREDITO"
    elif "DÉBITO" in m or "DEBITO" in m:
        return "TARJETA_DEBITO"
    elif "TRANSF" in m:
        return "TRANSFERENCIA"
    elif "VALE" in m:
        return "VALES"
    elif "PAYPAL" in m:
        return "PAYPAL"
    elif "MERCADO" in m:
        return "MERCADOPAGO"
    elif "OXXO" in m:
        return "OXXO_PAY"
    return m


def transformar_ventas_fisicas(
    df_raw: pd.DataFrame,
    catalogo_dict: Dict[str, Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Procesa las ventas físicas:
    - Detecta duplicados POS -> Cuarentena
    - Filtra cantidades <= 0 -> Cuarentena
    - Detecta llaves huérfanas -> Cuarentena
    - Imputa id_cliente faltante con 'ANONIMO' (MCAR)
    - Recalcula monto_total faltante
    - Homologa fechas y métodos de pago
    """
    valid_pids = set(catalogo_dict.keys())
    cuarentena = []
    candidatos_limpios = []

    # 1. Detección de duplicados exactos
    mask_duplicados = df_raw.duplicated(keep='first')
    for idx, row in df_raw[mask_duplicados].iterrows():
        cuarentena.append({
            "id_transaccion_origen": str(row.get('id_ticket', f'ROW_{idx}')),
            "fuente_origen": "VENTAS_TIENDA_FISICA",
            "motivo_rechazo_cuarentena": MOTIVO_DUPLICADO,
            "campo_erroneo": "id_ticket",
            "valor_invalido": str(row.get('id_ticket')),
            "datos_crudos_json": json.dumps(row.to_dict(), default=str)
        })

    df_sin_dups = df_raw[~mask_duplicados].copy()

    # 2. Iteración sobre registros únicos
    for idx, row in df_sin_dups.iterrows():
        id_ticket = str(row['id_ticket']).strip()
        cantidad = row['cantidad']
        id_prod = str(row['id_producto']).strip()

        # Validación de cantidad imposible
        if pd.isna(cantidad) or cantidad <= 0:
            cuarentena.append({
                "id_transaccion_origen": id_ticket,
                "fuente_origen": "VENTAS_TIENDA_FISICA",
                "motivo_rechazo_cuarentena": MOTIVO_CANTIDAD_INVALIDA,
                "campo_erroneo": "cantidad",
                "valor_invalido": str(cantidad),
                "datos_crudos_json": json.dumps(row.to_dict(), default=str)
            })
            continue

        # Validación de llave huérfana
        if id_prod not in valid_pids:
            cuarentena.append({
                "id_transaccion_origen": id_ticket,
                "fuente_origen": "VENTAS_TIENDA_FISICA",
                "motivo_rechazo_cuarentena": MOTIVO_PRODUCTO_HUERFANO,
                "campo_erroneo": "id_producto",
                "valor_invalido": str(id_prod),
                "datos_crudos_json": json.dumps(row.to_dict(), default=str)
            })
            continue

        # Homologación de fecha
        try:
            fecha_iso = normalizar_fecha(row['fecha_venta'])
        except Exception as e:
            cuarentena.append({
                "id_transaccion_origen": id_ticket,
                "fuente_origen": "VENTAS_TIENDA_FISICA",
                "motivo_rechazo_cuarentena": f"FECHA_INVALIDA: {str(e)}",
                "campo_erroneo": "fecha_venta",
                "valor_invalido": str(row['fecha_venta']),
                "datos_crudos_json": json.dumps(row.to_dict(), default=str)
            })
            continue

        # Imputación de categórica (MCAR)
        id_cliente = row['id_cliente']
        if pd.isna(id_cliente) or str(id_cliente).strip() == '':
            id_cliente = VALOR_IMPUTACION_CLIENTE
        else:
            id_cliente = str(id_cliente).strip()

        # Recálculo de precio e importe
        precio_unitario = float(row['precio_unitario'])
        monto_calculado = round(int(cantidad) * precio_unitario, 2)

        info_cat = catalogo_dict[id_prod]

        registro = {
            "id_transaccion": id_ticket,
            "fecha": fecha_iso,
            "canal": "FISICO",
            "sucursal": str(row['sucursal']).strip(),
            "id_producto": id_prod,
            "nombre_producto": info_cat['nombre_producto'],
            "categoria": info_cat['categoria'],
            "proveedor": info_cat['proveedor'],
            "cantidad": int(cantidad),
            "cantidad_original": int(cantidad),
            "precio_unitario_mxn": precio_unitario,
            "monto_total_mxn": monto_calculado,
            "monto_total_original": monto_calculado,
            "id_cliente": id_cliente,
            "cliente_email": None,
            "direccion_envio": "VENTA_EN_MOSTRADOR",
            "metodo_pago": homologar_metodo_pago(row['metodo_pago']),
            "estado_transaccion": "COMPLETADO"
        }
        candidatos_limpios.append(registro)

    return candidatos_limpios, cuarentena


def transformar_ventas_online(
    df_raw: pd.DataFrame,
    catalogo_dict: Dict[str, Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Procesa las ventas digitales:
    - Detecta llaves huérfanas -> Cuarentena
    - Valida correo electrónico estricto -> Cuarentena si ausente/malformado
    - Convierte USD a MXN al tipo de cambio oficial ($19.50)
    - Recalcula importe total (corrigiendo anomalías y bots)
    - Imputa dirección de envío faltante con 'SIN_DIRECCION'
    - Homologa fecha Unix / ISO a YYYY-MM-DD
    """
    valid_pids = set(catalogo_dict.keys())
    cuarentena = []
    candidatos_limpios = []

    for idx, row in df_raw.iterrows():
        order_id = str(row['order_id']).strip()
        id_prod = str(row['product_id']).strip()
        email = row.get('customer_email')

        # 1. Validación de llave huérfana
        if id_prod not in valid_pids:
            cuarentena.append({
                "id_transaccion_origen": order_id,
                "fuente_origen": "VENTAS_ONLINE",
                "motivo_rechazo_cuarentena": MOTIVO_PRODUCTO_HUERFANO,
                "campo_erroneo": "product_id",
                "valor_invalido": str(id_prod),
                "datos_crudos_json": json.dumps(row.to_dict(), default=str)
            })
            continue

        # 2. Validación estricta de correo electrónico
        if not email or pd.isna(email) or not isinstance(email, str) or not EMAIL_REGEX.match(email.strip()):
            cuarentena.append({
                "id_transaccion_origen": order_id,
                "fuente_origen": "VENTAS_ONLINE",
                "motivo_rechazo_cuarentena": MOTIVO_CORREO_INVALIDO,
                "campo_erroneo": "customer_email",
                "valor_invalido": str(email),
                "datos_crudos_json": json.dumps(row.to_dict(), default=str)
            })
            continue

        # 3. Homologación de fecha
        try:
            fecha_iso = normalizar_fecha(row['order_timestamp'])
        except Exception as e:
            cuarentena.append({
                "id_transaccion_origen": order_id,
                "fuente_origen": "VENTAS_ONLINE",
                "motivo_rechazo_cuarentena": f"FECHA_ONLINE_INVALIDA: {str(e)}",
                "campo_erroneo": "order_timestamp",
                "valor_invalido": str(row['order_timestamp']),
                "datos_crudos_json": json.dumps(row.to_dict(), default=str)
            })
            continue

        # 4. Manejo de divisas (USD a MXN)
        moneda = str(row.get('currency', 'MXN')).strip().upper()
        precio_raw = float(row['unit_price'])
        unidades = int(row['units'])

        if moneda == 'USD':
            precio_unitario_mxn = round(precio_raw * TIPO_CAMBIO_USD_MXN, 2)
        else:
            precio_unitario_mxn = round(precio_raw, 2)

        # Recálculo de total_amount legítimo (resuelve anomalías de compras distorsionadas)
        monto_calculado = round(unidades * precio_unitario_mxn, 2)

        # Imputación de dirección (MAR / MCAR)
        direccion = row.get('shipping_address')
        if not direccion or pd.isna(direccion) or str(direccion).strip() == '':
            direccion = VALOR_IMPUTACION_DIRECCION
        else:
            direccion = str(direccion).strip()

        info_cat = catalogo_dict[id_prod]

        registro = {
            "id_transaccion": order_id,
            "fecha": fecha_iso,
            "canal": "ONLINE",
            "sucursal": "TIENDA_WEB_OFICIAL",
            "id_producto": id_prod,
            "nombre_producto": info_cat['nombre_producto'],
            "categoria": info_cat['categoria'],
            "proveedor": info_cat['proveedor'],
            "cantidad": unidades,
            "cantidad_original": unidades,
            "precio_unitario_mxn": precio_unitario_mxn,
            "monto_total_mxn": monto_calculado,
            "monto_total_original": monto_calculado,
            "id_cliente": f"CTE_WEB_{order_id.replace('WEB-', '')}",
            "cliente_email": email.strip(),
            "direccion_envio": direccion,
            "metodo_pago": homologar_metodo_pago(row.get('payment_gateway')),
            "estado_transaccion": str(row.get('order_status', 'COMPLETADO')).strip().upper()
        }
        candidatos_limpios.append(registro)

    return candidatos_limpios, cuarentena


def aplicar_capping_iqr_cantidades(
    registros: List[Dict[str, Any]],
    factor: float = IQR_FACTOR
) -> Tuple[List[Dict[str, Any]], Dict[str, float]]:
    """
    Fase 3: Tratamiento de Outliers con IQR (Capping / Winsorizing).
    Calcula IQR = Q3 - Q1 en 'cantidad', define umbral superior = Q3 + 1.5 * IQR.
    Aplica Winsorizing recortando las compras gigantescas a dicho umbral sin pérdida destructiva.
    """
    cantidades = [r['cantidad'] for r in registros]
    q1 = float(np.percentile(cantidades, 25))
    q3 = float(np.percentile(cantidades, 75))
    iqr = q3 - q1
    umbral_superior = q3 + (factor * iqr)
    limite_cap = int(np.floor(umbral_superior))

    conteo_cappeados = 0
    for r in registros:
        if r['cantidad'] > limite_cap:
            r['cantidad'] = limite_cap
            # Actualizamos monto recalculado con cantidad cappeada
            r['monto_total_mxn'] = round(r['cantidad'] * r['precio_unitario_mxn'], 2)
            conteo_cappeados += 1

    stats_iqr = {
        "q1": round(q1, 2),
        "q3": round(q3, 2),
        "iqr": round(iqr, 2),
        "umbral_superior": round(umbral_superior, 2),
        "limite_capping": limite_cap,
        "registros_cappeados": conteo_cappeados
    }
    return registros, stats_iqr


def aplicar_escalamiento_y_discretizacion(
    registros: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Fase 5: Transformación, Discretización y Escalamiento.
    - Aplica normalización Min-Max en rango [0, 1] sobre monto_total_mxn.
    - Discretiza monto_total_mxn en 3 segmentos: 'Bajo', 'Medio', 'Alto' mediante cuantiles.
    """
    if not registros:
        return registros, {}

    montos = np.array([r['monto_total_mxn'] for r in registros])
    min_monto = float(montos.min())
    max_monto = float(montos.max())
    rango = max_monto - min_monto if max_monto > min_monto else 1.0

    # Terciles estadísticos para discretización de importes
    tercil_1 = float(np.percentile(montos, 33.33))
    tercil_2 = float(np.percentile(montos, 66.67))

    for r in registros:
        m = r['monto_total_mxn']
        # Min-Max
        norm_val = round(float((m - min_monto) / rango), 4)
        r['monto_escalado_minmax'] = max(0.0, min(1.0, norm_val))

        # Discretización
        if m <= tercil_1:
            r['segmento_monto'] = "Bajo"
        elif m <= tercil_2:
            r['segmento_monto'] = "Medio"
        else:
            r['segmento_monto'] = "Alto"

    stats_escalamiento = {
        "min_monto": round(min_monto, 2),
        "max_monto": round(max_monto, 2),
        "tercil_1": round(tercil_1, 2),
        "tercil_2": round(tercil_2, 2),
        "total_procesados": len(registros)
    }
    return registros, stats_escalamiento
