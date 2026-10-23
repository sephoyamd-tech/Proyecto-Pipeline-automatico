"""
Generador de Reporte Técnico Formal en PDF
Utiliza ReportLab para compilar el documento de entrega final del Proyecto Integrador.
"""
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

def generar_pdf():
    pdf_filename = "REPORTE_PROYECTO_ETL_GRUPO1.pdf"
    doc = SimpleDocTemplate(
        pdf_filename,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    
    # Estilos tipográficos ejecutivos
    primary_color = colors.HexColor("#0f172a")
    accent_amber = colors.HexColor("#d97706")
    text_dark = colors.HexColor("#1e293b")
    border_gray = colors.HexColor("#cbd5e1")
    bg_light = colors.HexColor("#f8fafc")

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=primary_color,
        spaceAfter=6
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=accent_amber,
        spaceAfter=14
    )

    h1_style = ParagraphStyle(
        'Heading1_Custom',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=primary_color,
        spaceBefore=12,
        spaceAfter=6
    )

    body_style = ParagraphStyle(
        'Body_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=text_dark,
        spaceAfter=6
    )

    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.white
    )

    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10.5,
        textColor=text_dark
    )

    elements = []

    # =========================================================================
    # ENCABEZADO INSTITUCIONAL
    # =========================================================================
    elements.append(Paragraph("TECNOLÓGICO NACIONAL DE MÉXICO", subtitle_style))
    elements.append(Paragraph("INSTITUTO TECNOLÓGICO DE COLIMA | DPTO. DE SISTEMAS Y COMPUTACIÓN", subtitle_style))
    elements.append(Paragraph("REPORTE TÉCNICO: PIPELINE ETL ROBUSTO CON ZONA DE CUARENTENA", title_style))
    elements.append(Paragraph("Materia: Ingeniería de Datos (ATD-2602) | Unidad 2: Limpieza y Preprocesamiento de Datos | Grupo 1 (LCS2)", subtitle_style))
    elements.append(HRFlowable(width="100%", thickness=2, color=accent_amber, spaceAfter=12))

    # =========================================================================
    # MATRIZ DE ROLES Y RESPONSABILIDADES
    # =========================================================================
    elements.append(Paragraph("1. Organización y Matriz de Responsabilidades (3 Integrantes)", h1_style))
    roles_data = [
        [Paragraph("Rol de Ingeniería", table_header_style), 
         Paragraph("Especialidad", table_header_style), 
         Paragraph("Responsabilidades Técnicas Específicas", table_header_style), 
         Paragraph("Entregable Clave", table_header_style)],
        
        [Paragraph("<b>Ingeniero/a 1</b>", table_cell_style),
         Paragraph("Calidad, Nulos y Outliers", table_cell_style),
         Paragraph("• Perfilado inicial cuantitativo de datos crudos.<br/>• Clasificación de ausencias MCAR/MAR e imputación estadística con mediana.<br/>• Detección de outliers con IQR (1.5) y aplicación de Capping / Winsorizing.", table_cell_style),
         Paragraph("Módulo de limpieza estadística + Reporte comparativo.", table_cell_style)],
        
        [Paragraph("<b>Ingeniero/a 2</b>", table_cell_style),
         Paragraph("Transformación e Integración", table_cell_style),
         Paragraph("• Fusión de fuentes heterogéneas (CSV físico + JSON web).<br/>• Homologación de fechas a ISO YYYY-MM-DD y conversión USD a MXN ($19.50).<br/>• Cruce con catálogo maestro y detección de llaves huérfanas.<br/>• Escalamiento Min-Max [0, 1] y discretización en 3 segmentos.", table_cell_style),
         Paragraph("Módulo de integración multifuente y normalización.", table_cell_style)],
        
        [Paragraph("<b>Ingeniero/a 3</b>", table_cell_style),
         Paragraph("Validación, Resiliencia y BD", table_cell_style),
         Paragraph("• Modelado de clases BaseModel con Pydantic y validadores personalizados @field_validator.<br/>• Mecanismo de segregación: registros conformes vs. zona de cuarentena con causa auditable.<br/>• Persistencia en SQLite relacional con transacciones seguras (commit/rollback).<br/>• Batería de pruebas de estrés con inyección de datos corruptos.", table_cell_style),
         Paragraph("Esquemas Pydantic + Script de carga transaccional + Pruebas de estrés.", table_cell_style)]
    ]

    t_roles = Table(roles_data, colWidths=[1.1*inch, 1.3*inch, 3.4*inch, 1.6*inch])
    t_roles.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('GRID', (0,0), (-1,-1), 0.5, border_gray),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, bg_light]),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    elements.append(t_roles)
    elements.append(Spacer(1, 10))

    # =========================================================================
    # RESUMEN EJECUTIVO Y MÉTRICAS DE EJECUCIÓN
    # =========================================================================
    elements.append(Paragraph("2. Resumen Ejecutivo de Ingestión y Resultados del Pipeline", h1_style))
    elements.append(Paragraph(
        "El pipeline procesó end-to-end la totalidad de los datos asignados al Grupo 1 (Retail & E-commerce Omnicanal). "
        "A través de un esquema de arquitectura tolerante a fallos, se logró procesar el 100% del volumen ingerido sin excepciones "
        "no controladas (Principio <i>No Crash</i>), canalizando las anomalías hacia la Zona de Cuarentena.", body_style
    ))

    metricas_data = [
        [Paragraph("Métrica de Pipeline", table_header_style), Paragraph("Valor Cuantitativo", table_header_style), Paragraph("Interpretación de Ingeniería", table_header_style)],
        [Paragraph("Total Registros Crudos Ingeridos", table_cell_style), Paragraph("<b>1,220</b> transacciones", table_cell_style), Paragraph("620 de Tienda Física (CSV) + 600 de Tienda Web (JSON)", table_cell_style)],
        [Paragraph("Transacciones Conformes (Aprobadas)", table_cell_style), Paragraph("<b>1,084</b> (88.85%)", table_cell_style), Paragraph("Persistidas exitosamente en tabla <i>transacciones_limpias</i> (SQLite)", table_cell_style)],
        [Paragraph("Desviadas a Zona de Cuarentena", table_cell_style), Paragraph("<b>136</b> (11.15%)", table_cell_style), Paragraph("Aisladas con causa en tabla <i>cuarentena_errores</i> con JSON crudo auditable", table_cell_style)],
        [Paragraph("Catálogo Maestro Registrado", table_cell_style), Paragraph("<b>50</b> productos", table_cell_style), Paragraph("Cargados en tabla relacional <i>catalogo_productos</i>", table_cell_style)],
        [Paragraph("Duplicados POS Neutralizados", table_cell_style), Paragraph("<b>20</b> registros", table_cell_style), Paragraph("Doble escaneo de tickets aislados en cuarentena", table_cell_style)],
        [Paragraph("Valores Imposibles (Cantidades <= 0)", table_cell_style), Paragraph("<b>11</b> transacciones", table_cell_style), Paragraph("Cantidades negativas (-1) o cero desviadas a cuarentena", table_cell_style)],
        [Paragraph("Productos Huérfanos Aislados", table_cell_style), Paragraph("<b>60</b> compras", table_cell_style), Paragraph("IDs no existentes en catálogo (PROD-9xx en física y PROD-8xx en online)", table_cell_style)],
        [Paragraph("Correos Malformados / Nulos", table_cell_style), Paragraph("<b>45</b> pedidos web", table_cell_style), Paragraph("Rechazados por validador Pydantic por no cumplir estándar RFC 5322", table_cell_style)],
        [Paragraph("Compras Gigantes Cappeadas con IQR", table_cell_style), Paragraph("<b>13</b> transacciones", table_cell_style), Paragraph("Compras de bots (99 y 500 uds) recortadas al umbral de 6 uds sin pérdida destructiva", table_cell_style)],
        [Paragraph("Conversión de Divisas USD a MXN", table_cell_style), Paragraph("<b>193</b> transacciones", table_cell_style), Paragraph("Convertidas a moneda nacional a tasa oficial de $19.50 MXN/USD", table_cell_style)]
    ]

    t_metricas = Table(metricas_data, colWidths=[2.2*inch, 1.6*inch, 3.6*inch])
    t_metricas.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, border_gray),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, bg_light]),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    elements.append(t_metricas)
    elements.append(Spacer(1, 10))

    # =========================================================================
    # FASE 2 & FASE 3: IMPUTACIÓN Y OUTLIERS
    # =========================================================================
    elements.append(Paragraph("3. Tratamiento Estadístico de Faltantes y Outliers (Fases 2 y 3)", h1_style))
    elements.append(Paragraph(
        "<b>Clasificación de Ausencias (MCAR vs MAR):</b><br/>"
        "• <i>id_cliente (MCAR):</i> Faltante en 127 registros físicos (20.5%). Corresponde a clientes walk-in que pagan en mostrador sin tarjeta de lealtad. Se imputó con la etiqueta categórica controlada <code>'ANONIMO'</code>.<br/>"
        "• <i>monto_total_mxn:</i> Faltante en 32 ventas físicas. Se recalculó determinísticamente mediante <code>monto_total = cantidad * precio_unitario</code>, garantizando 0% de pérdida de información.<br/>"
        "• <i>Justificación de la Mediana sobre la Media:</i> En distribuciones sesgadas por compras de bots (donde existen valores de 500 unidades y montos de millones de pesos), la media aritmética (<b>$16,586.74</b>) colapsa ante los outliers. La mediana (<b>$3,506.37</b>) preserva el valor representativo no paramétrico del 50% central.<br/>"
        "• <i>Capping con IQR (Winsorizing):</i> Se calculó IQR = Q3 - Q1 = 2.0 unidades. El umbral superior fijado fue <code>Q3 + 1.5 * IQR = 6.0 unidades</code>. Las compras gigantes fueron recortadas a 6 unidades sin eliminar la transacción, manteniendo el registro histórico en <code>cantidad_original</code>.",
        body_style
    ))

    if Path("grafico_outliers_iqr.png").exists():
        elements.append(Image("grafico_outliers_iqr.png", width=6.8*inch, height=3.0*inch))
        elements.append(Spacer(1, 10))

    # =========================================================================
    # FASE 4, 5 Y CUARENTENA
    # =========================================================================
    elements.append(Paragraph("4. Normalización Multifuente y Auditoría de Cuarentena (Fases 4, 5 y 6)", h1_style))
    elements.append(Paragraph(
        "<b>Estandarización Multifuente:</b> Las fechas heterogéneas (DD-MM-YYYY, DD/MM/YYYY y marcas Unix enteras) se unificaron al estándar ISO <code>YYYY-MM-DD</code>. "
        "Los importes en USD se convirtieron a MXN a $19.50. El importe final fue escalado mediante Min-Max en el rango [0, 1] y discretizado en 3 terciles: "
        "<b>Bajo</b> (hasta $2,069.07), <b>Medio</b> ($2,069.07 a $4,214.12) y <b>Alto</b> (más de $4,214.12).", body_style
    ))

    if Path("grafico_canales_segmentos.png").exists():
        elements.append(Image("grafico_canales_segmentos.png", width=6.8*inch, height=3.0*inch))
        elements.append(Spacer(1, 10))

    if Path("grafico_cuarentena_motivos.png").exists():
        elements.append(Image("grafico_cuarentena_motivos.png", width=6.8*inch, height=3.2*inch))
        elements.append(Spacer(1, 10))

    # =========================================================================
    # FASE 6 & 7: VALIDACIÓN PYDANTIC, PERSISTENCIA Y RESILIENCIA
    # =========================================================================
    elements.append(Paragraph("5. Validación Pydantic, Persistencia Transaccional y Pruebas de Estrés", h1_style))
    elements.append(Paragraph(
        "<b>Modelado Pydantic v2:</b> Se implementó la clase <code>TransaccionLimpiaSchema</code> con validadores <code>@field_validator</code> que evalúan tipos, "
        "rangos numéricos positivos, formato RFC 5322 en emails web e integridad ISO en fechas. Todo registro no conforme es capturado "
        "en un bloque <code>try ... except ValidationError</code> y redirigido a la tabla <code>cuarentena_errores</code> con trazabilidad auditable.<br/>"
        "<b>Persistencia Relacional Transaccional:</b> En SQLite (<code>retail_omnicanal.db</code>) se implementó manejo seguro de transacciones con bloques "
        "<code>conn.commit()</code> y <code>conn.rollback()</code>, garantizando atomicidad e integridad referencial contra el catálogo maestro.<br/>"
        "<b>Batería de Pruebas de Estrés (100% Aprobada):</b> Se ejecutaron 7 pruebas unitarias de inyección hostil (fechas corruptas, inyecciones SQL, "
        "cantidades negativas, llaves huérfanas masivas, ataques XSS en correos y fallos forzados de rollback), demostrando que el sistema opera bajo el principio <i>No Crash</i>.",
        body_style
    ))
    elements.append(Spacer(1, 14))

    # Firmas
    firmas_data = [
        [Paragraph("<b>Ingeniero/a 1</b><br/>Calidad, Nulos y Outliers", table_cell_style),
         Paragraph("<b>Ingeniero/a 2</b><br/>Transformación e Integración", table_cell_style),
         Paragraph("<b>Ingeniero/a 3</b><br/>Validación, Resiliencia y BD", table_cell_style)]
    ]
    t_firmas = Table(firmas_data, colWidths=[2.4*inch, 2.5*inch, 2.5*inch])
    t_firmas.setStyle(TableStyle([
        ('LINEABOVE', (0,0), (-1,-1), 1, primary_color),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('TOPPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(t_firmas)

    doc.build(elements)
    print(f"Reporte formal PDF generado exitosamente: {pdf_filename}")

if __name__ == "__main__":
    generar_pdf()
