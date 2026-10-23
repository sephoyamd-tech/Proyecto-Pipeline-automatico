"""
Generador de Gráficos de Calidad, Outliers y Cuarentena para Reportes y Dashboard
"""
import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')

from src.config import DATABASE_PATH

def generar_graficos():
    conn = sqlite3.connect(DATABASE_PATH)
    df_clean = pd.read_sql_query("SELECT * FROM transacciones_limpias;", conn)
    df_quar = pd.read_sql_query("SELECT * FROM cuarentena_errores;", conn)
    conn.close()

    # Estilo oscuro y limpio acorde a la paleta moderna
    plt.style.use('dark_background')
    plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
    plt.rcParams['axes.edgecolor'] = '#334155'
    plt.rcParams['axes.linewidth'] = 1.0

    # 1. Gráfico de Motivos de Cuarentena
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=300)
    conteo_motivos = df_quar['motivo_rechazo_cuarentena'].value_counts()
    colores = ['#ef4444', '#f97316', '#f59e0b', '#3b82f6']
    
    bars = ax.barh(conteo_motivos.index, conteo_motivos.values, color=colores[:len(conteo_motivos)], height=0.55)
    ax.set_title("Distribución de Registros en Zona de Cuarentena (136 Errores)", fontsize=13, fontweight='bold', color='#f8fafc', pad=15)
    ax.set_xlabel("Número de Registros Desviados", fontsize=10, color='#94a3b8')
    ax.grid(axis='x', linestyle='--', alpha=0.25)
    
    for bar in bars:
        w = bar.get_width()
        ax.text(w + 1, bar.get_y() + bar.get_height()/2, f"{int(w)} ({w/len(df_quar)*100:.1f}%)", 
                va='center', ha='left', color='#f8fafc', fontweight='bold', fontsize=9)
    
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.tight_layout()
    plt.savefig("grafico_cuarentena_motivos.png", facecolor='#0b0f19')
    plt.close()
    print("Generado: grafico_cuarentena_motivos.png")

    # 2. Gráfico de Tratamiento de Outliers (Cantidad Original vs Cantidad Cappeada)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.5), dpi=300)
    
    # Original
    ax1.boxplot(df_clean['cantidad_original'], patch_artist=True,
                boxprops=dict(facecolor='#1e293b', color='#ef4444', linewidth=1.5),
                medianprops=dict(color='#f59e0b', linewidth=2),
                flierprops=dict(marker='o', markerfacecolor='#ef4444', markersize=6, alpha=0.6))
    ax1.set_title("Antes: Cantidades Crudas con Bots\n(Valores extremos hasta 500 uds)", fontsize=11, fontweight='bold', color='#f8fafc')
    ax1.set_ylabel("Unidades por Transacción", color='#94a3b8')
    ax1.grid(axis='y', linestyle='--', alpha=0.2)
    
    # Cappeada con IQR
    ax2.boxplot(df_clean['cantidad'], patch_artist=True,
                boxprops=dict(facecolor='#1e293b', color='#10b981', linewidth=1.5),
                medianprops=dict(color='#38bdf8', linewidth=2),
                flierprops=dict(marker='o', markerfacecolor='#10b981', markersize=5, alpha=0.6))
    ax2.set_title("Después: Cantidades con IQR Capping\n(Recortado a umbral superior de 6 uds)", fontsize=11, fontweight='bold', color='#10b981')
    ax2.grid(axis='y', linestyle='--', alpha=0.2)
    
    plt.suptitle("Tratamiento Estadístico de Outliers con IQR (Winsorizing)", fontsize=13, fontweight='bold', color='#f8fafc')
    plt.tight_layout()
    plt.savefig("grafico_outliers_iqr.png", facecolor='#0b0f19')
    plt.close()
    print("Generado: grafico_outliers_iqr.png")

    # 3. Gráfico de Segmentación de Montos y Canales
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.5), dpi=300)
    
    # Canales
    conteo_canales = df_clean['canal'].value_counts()
    ax1.pie(conteo_canales.values, labels=conteo_canales.index, autopct='%1.1f%%',
            startangle=140, colors=['#3b82f6', '#10b981'], explode=(0.04, 0),
            textprops={'color': '#f8fafc', 'fontweight': 'bold'})
    ax1.set_title("Distribución por Canal Omnicanal", fontsize=11, fontweight='bold', color='#f8fafc')
    
    # Segmentos de Monto
    orden_segmentos = ['Bajo', 'Medio', 'Alto']
    conteo_seg = df_clean['segmento_monto'].value_counts().reindex(orden_segmentos)
    bars_seg = ax2.bar(orden_segmentos, conteo_seg.values, color=['#38bdf8', '#f59e0b', '#10b981'], width=0.5)
    ax2.set_title("Discretización en 3 Terciles de Importe", fontsize=11, fontweight='bold', color='#f8fafc')
    ax2.set_ylabel("Total de Transacciones", color='#94a3b8')
    ax2.grid(axis='y', linestyle='--', alpha=0.2)
    for b in bars_seg:
        h = b.get_height()
        ax2.text(b.get_x() + b.get_width()/2, h + 8, f"{int(h)}", ha='center', va='bottom', color='#f8fafc', fontweight='bold')

    plt.suptitle("Normalización y Segmentación Multifuente", fontsize=13, fontweight='bold', color='#f8fafc')
    plt.tight_layout()
    plt.savefig("grafico_canales_segmentos.png", facecolor='#0b0f19')
    plt.close()
    print("Generado: grafico_canales_segmentos.png")

if __name__ == "__main__":
    generar_graficos()
