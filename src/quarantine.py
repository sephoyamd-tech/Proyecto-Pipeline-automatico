"""
Módulo de Validación con Pydantic y Gestión de Zona de Cuarentena (Fase 6)
Ejecuta la validación estricta y captura excepciones ValidationError sin detener el pipeline.
"""
import json
from typing import List, Dict, Any, Tuple
from datetime import datetime
from pydantic import ValidationError
from src.schemas import TransaccionLimpiaSchema, CuarentenaRegistroSchema
from src.config import MOTIVO_PYDANTIC_FALLO

def segregar_con_pydantic(
    registros_candidatos: List[Dict[str, Any]],
    cuarentena_existente: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Fase 6: Validación con Pydantic y Cuarentena.
    Pasa cada registro por TransaccionLimpiaSchema.
    - Si cumple todas las reglas -> Se aprueba para la tabla final transacciones_limpias.
    - Si viola el esquema -> Se atrapa en try...except ValidationError y se desvía
      a cuarentena_errores guardando motivo_rechazo_cuarentena y el campo causante.
    """
    transacciones_conformes = []
    lista_cuarentena = list(cuarentena_existente)

    for item in registros_candidatos:
        try:
            # Validación estricta con Pydantic v2
            validado = TransaccionLimpiaSchema(**item)
            transacciones_conformes.append(validado.model_dump())
        except ValidationError as val_err:
            # Captura de error de esquema Pydantic
            primer_error = val_err.errors()[0]
            campo_fallido = ".".join(str(loc) for loc in primer_error.get('loc', ['desconocido']))
            mensaje_error = primer_error.get('msg', 'Error de validación de esquema')

            registro_cuarentena = CuarentenaRegistroSchema(
                id_transaccion_origen=str(item.get('id_transaccion', 'ID_DESCONOCIDO')),
                fuente_origen=f"TRANSFORM_{item.get('canal', 'DESCONOCIDO')}",
                motivo_rechazo_cuarentena=f"{MOTIVO_PYDANTIC_FALLO}: {mensaje_error}",
                campo_erroneo=campo_fallido,
                valor_invalido=str(item.get(campo_fallido, 'N/A')),
                datos_crudos_json=json.dumps(item, default=str)
            )
            lista_cuarentena.append(registro_cuarentena.model_dump())
        except Exception as generic_err:
            # Blindaje contra cualquier error inesperado (Principio no crash)
            registro_cuarentena = CuarentenaRegistroSchema(
                id_transaccion_origen=str(item.get('id_transaccion', 'ID_DESCONOCIDO')),
                fuente_origen=f"SISTEMA_{item.get('canal', 'DESCONOCIDO')}",
                motivo_rechazo_cuarentena=f"EXCEPCION_INESPERADA: {str(generic_err)}",
                campo_erroneo="sistema",
                valor_invalido="N/A",
                datos_crudos_json=json.dumps(item, default=str)
            )
            lista_cuarentena.append(registro_cuarentena.model_dump())

    # Garantizar que todos los registros en lista_cuarentena cumplan el esquema CuarentenaRegistroSchema
    cuarentena_estandarizada = []
    for item in lista_cuarentena:
        if isinstance(item, dict) and 'fecha_ingestion' not in item:
            item['fecha_ingestion'] = datetime.now().isoformat()
        cuarentena_estandarizada.append(item)

    return transacciones_conformes, cuarentena_estandarizada
