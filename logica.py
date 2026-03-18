from datetime import datetime, timedelta
from database import DatabaseManager
from clases import (
    HabitacionFactory,
    Reserva,
    PilaPersonalizada,
    Sujeto,
    Observador,
)

class DatabaseLogger(Observador):
    """Observador que guarda logs en la base de datos."""
    def __init__(self, db_name: str):
        self.db_name = db_name

    def actualizar(self, mensaje: str):
        conn = DatabaseManager.get_connection(self.db_name)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO logs (mensaje) VALUES (?)", (mensaje,))
        conn.commit()
        conn.close()

class SistemaReservasHotel(Sujeto):
    """Sistema principal de reservas del hotel."""
    def __init__(self, db_name: str):
        super().__init__()
        self.db_name = db_name
        self.habitaciones = []
        self.pila_reservas_actuales = PilaPersonalizada(100)
        self.pila_deshacer = PilaPersonalizada(100)

        DatabaseManager.setup(self.db_name)
        self.cargar_datos_desde_bd()
        self.contador_reservas = self.obtener_siguiente_id()
        self.agregar_observador(DatabaseLogger(self.db_name))

    def obtener_siguiente_id(self) -> int:
        """Obtiene el siguiente ID disponible para reservas."""
        conn = DatabaseManager.get_connection(self.db_name)
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(id_reserva) FROM reservas")
        max_id = cursor.fetchone()[0]
        conn.close()
        return (max_id or 0) + 1

    def cargar_datos_desde_bd(self):
        """Carga habitaciones y reservas desde la base de datos."""
        conn = DatabaseManager.get_connection(self.db_name)
        cursor = conn.cursor()
        self.habitaciones = []
        cursor.execute("SELECT * FROM habitaciones")
        for row in cursor.fetchall():
            self.habitaciones.append(HabitacionFactory.crear_habitacion(row["tipo"], row["numero"]))

        def buscar_habitacion(numero):
            return next((h for h in self.habitaciones if h.numero == numero), None)

        # Reservas actuales
        cursor.execute("SELECT * FROM reservas WHERE estado_pila = 'ACTUAL' ORDER BY id_reserva ASC")
        for r in cursor.fetchall():
            hab = buscar_habitacion(r["numero_habitacion"])
            if hab:
                self.pila_reservas_actuales.push(Reserva(r["id_reserva"], hab, r["fecha_inicio"], r["fecha_fin"], r["cliente"]))

        # Reservas para deshacer
        cursor.execute("SELECT * FROM reservas WHERE estado_pila = 'DESHACER' ORDER BY id_reserva ASC")
        for r in cursor.fetchall():
            hab = buscar_habitacion(r["numero_habitacion"])
            if hab:
                self.pila_deshacer.push(Reserva(r["id_reserva"], hab, r["fecha_inicio"], r["fecha_fin"], r["cliente"]))
        conn.close()

    def esta_ocupada(self, numero_habitacion: int, inicio: str, fin: str) -> bool:
        """Verifica si una habitación está ocupada en un rango de fechas."""
        try:
            fecha_inicio = datetime.strptime(inicio, "%Y-%m-%d")
            fecha_fin = datetime.strptime(fin, "%Y-%m-%d")
        except: return True

        temp = []
        ocupada = False
        while not self.pila_reservas_actuales.is_empty():
            reserva = self.pila_reservas_actuales.pop()
            if reserva.habitacion.numero == numero_habitacion:
                ri = datetime.strptime(reserva.fecha_inicio, "%Y-%m-%d")
                rf = datetime.strptime(reserva.fecha_fin, "%Y-%m-%d")
                if fecha_inicio < rf and fecha_fin > ri:
                    ocupada = True
            temp.append(reserva)
        for reserva in reversed(temp):
            self.pila_reservas_actuales.push(reserva)
        return ocupada

    def calculate_total_precio(self, habitacion, inicio: str, fin: str):
        """Calcula el precio total de una estancia."""
        try:
            actual = datetime.strptime(inicio, "%Y-%m-%d")
            final = datetime.strptime(fin, "%Y-%m-%d")
            total = 0.0
            while actual < final:
                total += habitacion.get_precio_noche(actual.strftime("%Y-%m-%d"))
                actual += timedelta(days=1)
            return round(total, 2)
        except: return 0.0

    def reservar_habitacion(self, cliente: str, inicio: str, fin: str, tipo: str = None, numero_habitacion: int = None) -> bool:
        """Realiza una reserva si hay disponibilidad."""
        if inicio >= fin: return False

        # Regla: No permitir fechas pasadas
        hoy = datetime.now().strftime("%Y-%m-%d")
        if inicio < hoy: return False

        # Selección de habitación
        if numero_habitacion:
            hab = next((h for h in self.habitaciones if h.numero == numero_habitacion), None)
            if not hab or self.esta_ocupada(hab.numero, inicio, fin): return False
        else:
            hab = None
            for h in self.habitaciones:
                if (not tipo or h.tipo == tipo) and not self.esta_ocupada(h.numero, inicio, fin):
                    hab = h
                    break
            if not hab: return False

        nueva = Reserva(self.contador_reservas, hab, inicio, fin, cliente)
        self.pila_reservas_actuales.push(nueva)
        self.contador_reservas += 1

        conn = DatabaseManager.get_connection(self.db_name)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO reservas VALUES (?, ?, ?, ?, ?, 'ACTUAL')",
                      (nueva.id_reserva, hab.numero, inicio, fin, cliente))
        conn.commit()
        conn.close()
        self.notificar(f"RESERVA: {cliente} | Hab #{hab.numero} | {inicio} a {fin}")
        return True

    def cancelar_reserva_lifo(self) -> bool:
        """Cancela la última reserva (LIFO)."""
        if self.pila_reservas_actuales.is_empty(): return False
        reserva = self.pila_reservas_actuales.pop()
        return self._procesar_cancelacion(reserva)

    def cancelar_reserva(self, id_reserva: int) -> bool:
        """Busca una reserva específica por ID y la cancela."""
        temp = []
        encontrada = None
        while not self.pila_reservas_actuales.is_empty():
            r = self.pila_reservas_actuales.pop()
            if r.id_reserva == id_reserva:
                encontrada = r
                break
            temp.append(r)
        for r in reversed(temp):
            self.pila_reservas_actuales.push(r)
        if encontrada:
            return self._procesar_cancelacion(encontrada)
        return False

    def _procesar_cancelacion(self, reserva) -> bool:
        """Lógica compartida para procesar la cancelación de una reserva."""
        self.pila_deshacer.push(reserva)
        conn = DatabaseManager.get_connection(self.db_name)
        cursor = conn.cursor()
        cursor.execute("UPDATE reservas SET estado_pila='DESHACER' WHERE id_reserva=?", (reserva.id_reserva,))
        conn.commit()
        conn.close()
        self.notificar(f"CANCELACIÓN: Reserva {reserva.id_reserva} de {reserva.cliente}")
        return True

    def borrar_definitivamente_lifo(self) -> bool:
        """Elimina definitivamente la última reserva."""
        if self.pila_reservas_actuales.is_empty(): return False
        reserva = self.pila_reservas_actuales.pop()
        conn = DatabaseManager.get_connection(self.db_name)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM reservas WHERE id_reserva=?", (reserva.id_reserva,))
        conn.commit()
        conn.close()
        self.notificar(f"BORRADO DEFINITIVO: Reserva {reserva.id_reserva} de {reserva.cliente}")
        return True

    def deshacer_cancelacion(self) -> str:
        """Deshace la última cancelación."""
        if self.pila_deshacer.is_empty(): return "EMPTY"
        reserva = self.pila_deshacer.peek()
        if self.esta_ocupada(reserva.habitacion.numero, reserva.fecha_inicio, reserva.fecha_fin):
            return "OCCUPIED"
        self.pila_deshacer.pop()
        self.pila_reservas_actuales.push(reserva)
        conn = DatabaseManager.get_connection(self.db_name)
        cursor = conn.cursor()
        cursor.execute("UPDATE reservas SET estado_pila='ACTUAL' WHERE id_reserva=?", (reserva.id_reserva,))
        conn.commit()
        conn.close()
        self.notificar(f"DESHACER: Reserva {reserva.id_reserva} de {reserva.cliente} restaurada")
        return "OK"

    def obtener_estado_por_rango(self, inicio: str, fin: str):
        """Obtiene disponibilidad y precios por rango."""
        resultado = []
        for hab in self.habitaciones:
            datos = hab.to_dict()
            datos["disponible"] = not self.esta_ocupada(hab.numero, inicio, fin)
            datos["precio_total"] = self.calculate_total_precio(hab, inicio, fin)
            resultado.append(datos)
        return resultado

    def buscar_reservas(self, termino: str):
        """Busca reservas por cliente, habitación o fecha."""
        temp = []
        resultados = []
        t_lower = termino.lower()
        while not self.pila_reservas_actuales.is_empty():
            reserva = self.pila_reservas_actuales.pop()
            match = False
            if t_lower in reserva.cliente.lower(): match = True
            elif t_lower == str(reserva.habitacion.numero): match = True
            else:
                try:
                    fecha = datetime.strptime(termino, "%Y-%m-%d")
                    ri = datetime.strptime(reserva.fecha_inicio, "%Y-%m-%d")
                    rf = datetime.strptime(reserva.fecha_fin, "%Y-%m-%d")
                    if ri <= fecha < rf: match = True
                except: pass
            if match: resultados.append(reserva.to_dict())
            temp.append(reserva)
        for r in reversed(temp): self.pila_reservas_actuales.push(r)
        return resultados

    def obtener_logs(self):
        """Obtiene los últimos logs."""
        conn = DatabaseManager.get_connection(self.db_name)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM logs ORDER BY id DESC LIMIT 15")
        logs = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return logs
