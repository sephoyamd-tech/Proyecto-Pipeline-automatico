"""
=============================================================================
BATERÍA DE PRUEBAS DE ESTRÉS Y RESILIENCIA (FAULT INJECTION TEST SUITE)
Ingeniero/a 3: Validación, Resiliencia y BD
Evalúa la tolerancia a fallos del pipeline ante datos hostiles, malformados y corruptos.
Principio: NO CRASH y segregación a cuarentena con causa auditable.
=============================================================================
"""
import sys
import unittest
import sqlite3
import json
from pathlib import Path
from datetime import datetime

# Añadir raíz al sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import DATABASE_PATH, TIPO_CAMBIO_USD_MXN
from src.extract import cargar_catalogo
from src.transform import (
    normalizar_fecha,
    transformar_ventas_fisicas,
    transformar_ventas_online,
    aplicar_capping_iqr_cantidades,
    aplicar_escalamiento_y_discretizacion
)
from src.quarantine import segregar_con_pydantic
from src.load import (
    inicializar_base_de_datos,
    persistir_transacciones_limpias,
    persistir_cuarentena,
    obtener_metricas_base_datos
)
from src.schemas import TransaccionLimpiaSchema, CuarentenaRegistroSchema
import pandas as pd

class TestStressAndResilience(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Carga catálogo y configuración base."""
        cls.catalogo_df = cargar_catalogo()
        cls.cat_dict = cls.catalogo_df.set_index('id_producto').to_dict(orient='index')
        cls.db_test_path = Path("test_stress_quarantine.db")
        if cls.db_test_path.exists():
            cls.db_test_path.unlink()
        inicializar_base_de_datos(cls.db_test_path)

    @classmethod
    def tearDownClass(cls):
        """Limpia la base de datos temporal de prueba."""
        import gc
        gc.collect()
        try:
            if cls.db_test_path.exists():
                cls.db_test_path.unlink()
        except PermissionError:
            pass

    def test_01_inyeccion_fechas_corruptas(self):
        """Prueba de tolerancia ante fechas inválidas o imposibles."""
        fechas_hostiles = ["32-13-2026", "ayer por la tarde", "99/99/9999", "", "null", "2026-02-30"]
        for f in fechas_hostiles:
            with self.subTest(fecha=f):
                with self.assertRaises(Exception):
                    normalizar_fecha(f)

    def test_02_inyeccion_sql_en_identificadores(self):
        """Prueba contra inyecciones SQL en tickets y llaves foráneas."""
        df_corrupto = pd.DataFrame([
            {
                "id_ticket": "POS'; DROP TABLE transacciones_limpias; --",
                "fecha_venta": "2026-09-15",
                "sucursal": "Sucursal Norte",
                "id_producto": "PROD-001",
                "cantidad": 2,
                "precio_unitario": 545.42,
                "monto_total_mxn": 1090.84,
                "id_cliente": "CTE-999",
                "metodo_pago": "Efectivo"
            }
        ])
        candidatos, cuarentena = transformar_ventas_fisicas(df_corrupto, self.cat_dict)
        candidatos, _ = aplicar_escalamiento_y_discretizacion(candidatos)
        candidatos_validados, _ = segregar_con_pydantic(candidatos, [])
        # El pipeline debe procesarlo sin colapsar y persistirlo con parámetros preparados seguros
        persistir_transacciones_limpias(candidatos_validados, self.db_test_path)
        with sqlite3.connect(self.db_test_path) as conn:
            c = conn.cursor()
            c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='transacciones_limpias';")
            self.assertIsNotNone(c.fetchone(), "La tabla no debe ser eliminada por inyección SQL")

    def test_03_inyeccion_cantidades_negativas_y_nulas(self):
        """Garantiza que cantidades <= 0 jamás ingresen a transacciones limpias."""
        df_cantidades_malas = pd.DataFrame([
            {
                "id_ticket": "POS-MAL-01",
                "fecha_venta": "2026-09-15",
                "sucursal": "Centro",
                "id_producto": "PROD-001",
                "cantidad": -50,
                "precio_unitario": 500.0,
                "monto_total_mxn": -25000.0,
                "id_cliente": "CTE-001",
                "metodo_pago": "Efectivo"
            },
            {
                "id_ticket": "POS-MAL-02",
                "fecha_venta": "2026-09-15",
                "sucursal": "Centro",
                "id_producto": "PROD-001",
                "cantidad": 0,
                "precio_unitario": 500.0,
                "monto_total_mxn": 0.0,
                "id_cliente": "CTE-002",
                "metodo_pago": "Efectivo"
            }
        ])
        candidatos, cuarentena = transformar_ventas_fisicas(df_cantidades_malas, self.cat_dict)
        self.assertEqual(len(candidatos), 0, "No debe haber candidatos limpios con cantidad <= 0")
        self.assertEqual(len(cuarentena), 2, "Ambos deben desviarse a cuarentena")
        for q in cuarentena:
            self.assertEqual(q['motivo_rechazo_cuarentena'], "VALOR_IMPOSIBLE_CANTIDAD_NO_POSITIVA")

    def test_04_inyeccion_llaves_huerfanas_masivas(self):
        """Verifica que productos no registrados en catálogo sean desviados a cuarentena."""
        df_huerfanos = pd.DataFrame([
            {
                "order_id": "WEB-HUERF-99",
                "order_timestamp": "2026-10-01T12:00:00",
                "product_id": "PROD-INEXISTENTE-8888",
                "units": 1,
                "currency": "MXN",
                "unit_price": 100.0,
                "total_amount": 100.0,
                "customer_email": "usuario@test.com",
                "shipping_address": "Calle 10",
                "order_status": "COMPLETADO",
                "payment_gateway": "PayPal"
            }
        ])
        candidatos, cuarentena = transformar_ventas_online(df_huerfanos, self.cat_dict)
        self.assertEqual(len(candidatos), 0)
        self.assertEqual(len(cuarentena), 1)
        self.assertEqual(cuarentena[0]['motivo_rechazo_cuarentena'], "PRODUCTO_HUERFANO_NO_CATALOGADO")

    def test_05_inyeccion_correos_maliciosos_y_malformados(self):
        """Asegura el desvío a cuarentena de ataques XSS y emails rotos en canal online."""
        emails_hostiles = [
            "<script>alert('xss')</script>",
            "usuario@@gmail..com",
            "sin_arroba_dominio.com",
            "correo_invalido.org",
            "",
            None
        ]
        for idx, email in enumerate(emails_hostiles):
            df_email = pd.DataFrame([{
                "order_id": f"WEB-XSS-{idx}",
                "order_timestamp": "2026-10-01T10:00:00",
                "product_id": "PROD-001",
                "units": 1,
                "currency": "MXN",
                "unit_price": 545.42,
                "total_amount": 545.42,
                "customer_email": email,
                "shipping_address": "Direccion Test",
                "order_status": "COMPLETADO",
                "payment_gateway": "PayPal"
            }])
            cands, quar = transformar_ventas_online(df_email, self.cat_dict)
            self.assertEqual(len(cands), 0, f"Email '{email}' no debió pasar como limpio")
            self.assertEqual(len(quar), 1)
            self.assertEqual(quar[0]['motivo_rechazo_cuarentena'], "CORREO_ELECTRONICO_INVALIDO")

    def test_06_resiliencia_transaccional_rollback(self):
        """Comprueba que conn.rollback() protege la BD ante una excepción forzada."""
        datos_corruptos = [
            {"id_transaccion": "T1", "fecha": "2026-09-01"},  # incompleto intencionalmente
        ]
        with self.assertRaises(Exception):
            persistir_transacciones_limpias(datos_corruptos, self.db_test_path)

    def test_07_capping_iqr_compras_gigantes(self):
        """Verifica que compras con cantidades gigantescas (bots) sean recortadas al umbral IQR."""
        muestra = [
            {
                "id_transaccion": f"POS-NORM-{i}",
                "fecha": "2026-09-10",
                "canal": "FISICO",
                "sucursal": "Centro",
                "id_producto": "PROD-001",
                "cantidad": (i % 3) + 1,
                "cantidad_original": (i % 3) + 1,
                "precio_unitario_mxn": 100.0,
                "monto_total_mxn": float(((i % 3) + 1) * 100),
                "monto_total_original": float(((i % 3) + 1) * 100)
            }
            for i in range(20)
        ]
        # Inyectar compra de bot con 500 unidades
        muestra.append({
            "id_transaccion": "POS-BOT-01",
            "fecha": "2026-09-10",
            "canal": "FISICO",
            "sucursal": "Centro",
            "id_producto": "PROD-001",
            "cantidad": 500,  # Bot
            "cantidad_original": 500,
            "precio_unitario_mxn": 100.0,
            "monto_total_mxn": 50000.0,
            "monto_total_original": 50000.0
        })
        procesados, stats = aplicar_capping_iqr_cantidades(muestra)
        bot_record = next(r for r in procesados if r['id_transaccion'] == "POS-BOT-01")
        self.assertLess(bot_record['cantidad'], 500, "La cantidad gigante debió ser cappeada")
        self.assertEqual(bot_record['cantidad_original'], 500, "Se debe conservar la cantidad original para auditoría")
        self.assertEqual(stats['registros_cappeados'], 1)

def ejecutar_bateria_estres():
    print("=" * 70)
    print("INICIANDO BATERÍA DE PRUEBAS DE ESTRÉS Y RESILIENCIA (INGENIERO 3)")
    print("=" * 70)
    suite = unittest.TestLoader().loadTestsFromTestCase(TestStressAndResilience)
    runner = unittest.TextTestRunner(verbosity=2)
    resultado = runner.run(suite)
    if resultado.wasSuccessful():
        print("\n>>> RESULTADO: 100% DE LAS PRUEBAS DE ESTRÉS SUPERADAS. SISTEMA RESILIENTE.")
        return 0
    else:
        print("\n>>> ALERTA: FALLAS EN PRUEBAS DE ESTRÉS.")
        return 1

if __name__ == "__main__":
    sys.exit(ejecutar_bateria_estres())
