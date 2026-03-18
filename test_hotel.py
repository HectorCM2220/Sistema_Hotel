import unittest
import os
import sys
from datetime import datetime, timedelta
from logica import SistemaReservasHotel
from clases import PilaPersonalizada

class TestSistemaReservasHotel(unittest.TestCase):
    """
    Conjunto de pruebas unitarias profundas para el sistema de reservas del hotel.
    Cada prueba incluye mensajes detallados en caso de fallo para facilitar el diagnóstico.
    """
    DB_PRUEBA = "test_hotel.db"
    
    def setUp(self):
        """Prepara una base de datos limpia antes de cada prueba."""
        if os.path.exists(self.DB_PRUEBA):
            os.remove(self.DB_PRUEBA)
        self.hotel = SistemaReservasHotel(self.DB_PRUEBA)
    
    def tearDown(self):
        """Limpia la base de datos después de cada prueba."""
        if os.path.exists(self.DB_PRUEBA):
            os.remove(self.DB_PRUEBA)

    def test_01_inicializacion(self):
        """Verifica que el sistema inicie con 24 habitaciones y contadores en 1."""
        self.assertEqual(self.hotel.contador_reservas, 1, 
                         msg="El contador de reservas debería iniciar en 1.")
        self.assertEqual(len(self.hotel.habitaciones), 24, 
                         msg="El sistema debería cargar 24 habitaciones (10 Simples, 8 Dobles, 6 Suites).")
        self.assertTrue(self.hotel.pila_reservas_actuales.is_empty(), 
                        msg="La pila de reservas actuales debería estar vacía al inicio.")

    def test_02_reserva_simple_exitosa(self):
        """Verifica una reserva estándar de una noche."""
        res = self.hotel.reservar_habitacion("Juan Perez", "2027-05-10", "2027-05-11", "Simple")
        self.assertTrue(res, msg="La reserva para Juan Perez en una habitación Simple debería haber sido aceptada.")
        self.assertEqual(self.hotel.pila_reservas_actuales.size(), 1, 
                         msg="Debería haber exactamente 1 reserva en la pila tras la operación.")

    def test_03_bloqueo_por_fecha_invalida(self):
        """Verifica que no se permitan reservas donde la salida es antes que la entrada."""
        res = self.hotel.reservar_habitacion("Error", "2027-05-15", "2027-05-10", "Simple")
        self.assertFalse(res, msg="FALLO DE SEGURIDAD: El sistema permitió una reserva con fecha de salida anterior a la entrada.")

    def test_04_solapamiento_de_fechas(self):
        """Prueba crítica: Verifica que no se pueda reservar la misma habitación en fechas que chocan."""
        # Escenario: Habitación 102 ocupada del 10 al 15 de Junio
        self.hotel.reservar_habitacion("Cliente A", "2027-06-10", "2027-06-15", numero_habitacion=102)
        
        # Intento 1: Solapamiento idéntico
        res1 = self.hotel.reservar_habitacion("Cliente B", "2027-06-10", "2027-06-15", numero_habitacion=102)
        self.assertFalse(res1, msg="ERROR: Se permitió duplicar una reserva exacta para la misma habitación.")

        # Intento 2: Solapamiento parcial (el cliente quiere entrar antes de que el anterior salga)
        res2 = self.hotel.reservar_habitacion("Cliente C", "2027-06-12", "2027-06-18", numero_habitacion=102)
        self.assertFalse(res2, msg="ERROR: Se permitió una reserva que inicia antes de que termine la estancia previa en la misma habitación.")

        # Intento 3: Caso de borde (el cliente entra el mismo día que el anterior sale)
        res3 = self.hotel.reservar_habitacion("Cliente D", "2027-06-15", "2027-06-20", numero_habitacion=102)
        self.assertTrue(res3, msg="La reserva debería permitirse si el Check-In coincide con el Check-Out del anterior.")

    def test_05_busqueda_de_reservas(self):
        """Verifica que la función de búsqueda encuentre reservas por nombre o habitación."""
        # Preparamos datos: habitaciones 202 (Doble) y 302 (Suite)
        self.hotel.reservar_habitacion("Maria Garcia", "2027-07-01", "2027-07-05", numero_habitacion=202)
        self.hotel.reservar_habitacion("Pedro Infante", "2027-07-10", "2027-07-12", numero_habitacion=302)
        
        # Prueba: Búsqueda parcial por nombre
        resultados = self.hotel.buscar_reservas("Maria")
        self.assertEqual(len(resultados), 1, msg="La búsqueda por 'Maria' debería retornar exactamente 1 resultado.")
        self.assertEqual(resultados[0]['cliente'], "Maria Garcia", msg="El cliente encontrado no coincide con el buscado.")

        # Prueba: Búsqueda por número de habitación
        resultados_hab = self.hotel.buscar_reservas("302")
        self.assertEqual(len(resultados_hab), 1, msg="La búsqueda por habitación '302' debería retornar 1 resultado.")

    def test_06_precios_dinamicos(self):
        """Verifica que el precio cambie según el día de la semana (Reglas de negocio)."""
        hab_simple = self.hotel.habitaciones[0] # Hab 102 Simple (Precio base 50.0)
        
        # Regla: Lunes -10% -> 50.0 * 0.9 = 45.0
        # 2027-03-22 es Lunes
        precio_lunes = hab_simple.get_precio_noche("2027-03-22")
        self.assertEqual(precio_lunes, 45.0, msg="El precio para un Lunes debería tener un descuento del 10%.")

        # Regla: Sábado +20% -> 50.0 * 1.2 = 60.0
        # 2027-03-20 es Sábado
        precio_sabado = hab_simple.get_precio_noche("2027-03-20")
        self.assertEqual(precio_sabado, 60.0, msg="El precio para un Sábado debería tener un recargo del 20%.")

    def test_07_cancelacion_e_id_de_reserva(self):
        """Verifica que se pueda cancelar una reserva específica usando su ID único."""
        self.hotel.reservar_habitacion("C1", "2027-10-01", "2027-10-02") # ID 1
        self.hotel.reservar_habitacion("C2", "2027-10-05", "2027-10-06") # ID 2
        
        # Acción: Cancelar ID 1 (C1)
        exito = self.hotel.cancelar_reserva(1)
        self.assertTrue(exito, msg="El sistema debería permitir cancelar una reserva antigua mediante su ID.")
        self.assertEqual(self.hotel.pila_reservas_actuales.size(), 1, msg="Tras cancelar una de dos reservas, debería quedar 1.")
        self.assertEqual(self.hotel.pila_reservas_actuales.peek().cliente, "C2", 
                         msg="La reserva que quedó en la pila debería ser la del Cliente C2.")

    def test_08_bloqueo_fecha_pasada(self):
        """Verifica que no se permitan reservas en fechas anteriores a hoy."""
        # Suponiendo que 'hoy' es 2026-03-17 (basado en metadata), probamos con 2026-01-01
        fecha_pasada = "2026-01-01"
        fecha_fin = "2026-01-02"
        res = self.hotel.reservar_habitacion("Cliente Pasado", fecha_pasada, fecha_fin, "Simple")
        self.assertFalse(res, msg="ERROR: El sistema permitió una reserva en una fecha que ya pasó (2026-01-01).")

class TestPilaEstructura(unittest.TestCase):
    """
    Pruebas para validar la integridad de la estructura de datos PilaPersonalizada (LIFO).
    """
    
    def test_pila_vacia(self):
        """Verifica que la pila detecte cuando está vacía y lance excepciones adecuadas."""
        p = PilaPersonalizada(2)
        self.assertTrue(p.is_empty(), msg="La pila nueva debería reportar que está vacía.")
        with self.assertRaises(IndexError, msg="Sacar un elemento de una pila vacía debe lanzar IndexError."):
            p.pop()

    def test_pila_llena(self):
        """Verifica que se respete el límite de capacidad máxima."""
        p = PilaPersonalizada(2)
        p.push("A")
        p.push("B")
        self.assertTrue(p.is_full(), msg="La pila con 2 elementos y capacidad 2 debe reportar que está llena.")
        with self.assertRaises(OverflowError, msg="Superar la capacidad máxima debe lanzar OverflowError."):
            p.push("C")

    def test_orden_lifo(self):
        """Verifica que el orden de salida sea el inverso al de entrada (Last-In, First-Out)."""
        p = PilaPersonalizada(5)
        p.push("Primero")
        p.push("Segundo")
        self.assertEqual(p.pop(), "Segundo", msg="El primer elemento en salir debe ser el último que entró ('Segundo').")
        self.assertEqual(p.pop(), "Primero", msg="El siguiente debe ser el anterior ('Primero').")

class CustomResult(unittest.TextTestResult):
    """Clase personalizada para mostrar un reporte más amigable en consola."""
    def addSuccess(self, test):
        super().addSuccess(test)
        print(f"  ✓ {test._testMethodDoc or test._testMethodName}: EXITOSO")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        print(f"  ✗ {test._testMethodDoc or test._testMethodName}: FALLIDO")
        print(f"     DETALLE: {err[1]}")

    def addError(self, test, err):
        super().addError(test, err)
        print(f"  ⚠ {test._testMethodDoc or test._testMethodName}: ERROR DE CÓDIGO")

if __name__ == "__main__":
    print("\n" + "╔" + "═"*68 + "╗")
    print("║" + " "*10 + "INFORME DETALLADO DE PRUEBAS - SISTEMA HOTEL" + " "*14 + "║")
    print("╚" + "═"*68 + "╝\n")
    
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSistemaReservasHotel)
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestPilaEstructura))
    
    runner = unittest.TextTestRunner(verbosity=1, resultclass=CustomResult)
    resultado = runner.run(suite)
    
    print("\n" + "="*70)
    print(f" RESUMEN FINAL:")
    print(f" - Pruebas Totales: {resultado.testsRun}")
    print(f" - Exitosas: {resultado.testsRun - len(resultado.failures) - len(resultado.errors)}")
    
    if resultado.wasSuccessful():
        print(f" - Estado General: [ TODO CORRECTO ]")
        print("="*70 + "\n")
        sys.exit(0)
    else:
        print(f" - Fallos detectados: {len(resultado.failures)}")
        print(f" - Errores de código: {len(resultado.errors)}")
        print(f" - Estado General: [ REVISAR FALLOS ]")
        print("="*70 + "\n")
        sys.exit(1)
