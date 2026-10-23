"""
Módulo de Validación de Esquemas con Pydantic v2
Define los modelos estrictos de negocio y validadores decorados con @field_validator.
"""
from pydantic import BaseModel, Field, field_validator, ValidationInfo
from typing import Optional, Literal
from datetime import datetime
import re

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')
DATE_ISO_REGEX = re.compile(r'^\d{4}-\d{2}-\d{2}$')

class TransaccionLimpiaSchema(BaseModel):
    """
    Esquema estricto para transacciones conformes a cargar en la base de datos relacional.
    """
    id_transaccion: str = Field(..., description="Identificador único del ticket o pedido")
    fecha: str = Field(..., description="Fecha de la transacción homologada a ISO YYYY-MM-DD")
    canal: Literal['FISICO', 'ONLINE'] = Field(..., description="Canal de venta")
    sucursal: str = Field(..., description="Sucursal física o tienda web")
    id_producto: str = Field(..., description="Clave foránea hacia catalogo_productos")
    nombre_producto: str = Field(..., description="Nombre comercial del producto")
    categoria: str = Field(..., description="Categoría comercial")
    proveedor: str = Field(..., description="Proveedor asignado")
    cantidad: int = Field(..., description="Cantidad de unidades tras tratamiento de outliers")
    cantidad_original: int = Field(..., description="Cantidad de unidades crudas")
    precio_unitario_mxn: float = Field(..., description="Precio unitario normalizado en pesos mexicanos (MXN)")
    monto_total_mxn: float = Field(..., description="Importe total de la compra tras recálculo y capping")
    monto_total_original: float = Field(..., description="Importe total antes de tratamiento de outliers")
    monto_escalado_minmax: float = Field(..., description="Variable numérica normalizada en rango [0, 1]")
    segmento_monto: Literal['Bajo', 'Medio', 'Alto'] = Field(..., description="Discretización de importe")
    id_cliente: str = Field(..., description="Identificador de cliente o ANONIMO")
    cliente_email: Optional[str] = Field(None, description="Correo electrónico validado (requerido para online)")
    direccion_envio: Optional[str] = Field(None, description="Dirección de entrega física")
    metodo_pago: str = Field(..., description="Forma de pago homologada")
    estado_transaccion: str = Field(..., description="Estado del pedido (COMPLETADO, PENDIENTE, CANCELADO)")
    fecha_procesamiento: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Timestamp de ingesta")

    @field_validator('fecha')
    @classmethod
    def validar_formato_fecha_iso(cls, v: str) -> str:
        if not DATE_ISO_REGEX.match(v):
            raise ValueError(f"La fecha debe cumplir el estándar ISO YYYY-MM-DD, recibido: '{v}'")
        try:
            datetime.strptime(v, '%Y-%m-%d')
        except ValueError:
            raise ValueError(f"Fecha calendario inválida: '{v}'")
        return v

    @field_validator('cantidad')
    @classmethod
    def validar_cantidad_positiva(cls, v: int) -> int:
        if v <= 0:
            raise ValueError(f"La cantidad debe ser un entero estrictamente positivo (> 0), recibido: {v}")
        return v

    @field_validator('precio_unitario_mxn', 'monto_total_mxn')
    @classmethod
    def validar_importes_monetarios(cls, v: float) -> float:
        if v <= 0:
            raise ValueError(f"El importe monetario debe ser positivo (> 0), recibido: {v}")
        return round(float(v), 2)

    @field_validator('monto_escalado_minmax')
    @classmethod
    def validar_rango_minmax(cls, v: float) -> float:
        if not (-0.0001 <= v <= 1.0001):
            raise ValueError(f"El escalamiento Min-Max debe ubicarse en el intervalo [0, 1], recibido: {v}")
        return round(float(max(0.0, min(1.0, v))), 4)

    @field_validator('cliente_email')
    @classmethod
    def validar_email_si_online(cls, v: Optional[str], info: ValidationInfo) -> Optional[str]:
        # Para el canal ONLINE, no se permite correo nulo o malformado
        canal = info.data.get('canal')
        if canal == 'ONLINE':
            if not v or not isinstance(v, str) or not EMAIL_REGEX.match(v.strip()):
                raise ValueError(f"Correo electrónico inválido o ausente en canal online: '{v}'")
        return v.strip() if isinstance(v, str) else v


class CuarentenaRegistroSchema(BaseModel):
    """
    Esquema para auditoría de registros rechazados en la Zona de Cuarentena.
    """
    id_transaccion_origen: str = Field(..., description="ID del ticket o pedido rechazado")
    fuente_origen: str = Field(..., description="Archivo de origen (VENTAS_TIENDA_FISICA / VENTAS_ONLINE)")
    fecha_ingestion: str = Field(default_factory=lambda: datetime.now().isoformat())
    motivo_rechazo_cuarentena: str = Field(..., description="Causa técnica estandarizada del desvío")
    campo_erroneo: str = Field(..., description="Columna o variable que provocó la falla")
    valor_invalido: str = Field(..., description="Valor específico no conforme")
    datos_crudos_json: str = Field(..., description="Copia exacta en JSON del payload crudo para auditoría")
