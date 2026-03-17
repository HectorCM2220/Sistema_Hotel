from datetime import datetime, timedelta

from database import DatabaseManager
from clases import (
    HabitacionFactory,
    Reserva,
    PilaPersonalizada,
    Sujeto,
    Observador,
)


# --- Implementación del Observador para Logs ---
class DatabaseLogger(Observador):
    """Observador que guarda logs en la base de datos."""

    def __init__(self, db_name: str):
        self.db_name = db_name

    def actualizar(self, mensaje: str):
        conn = DatabaseManager.get_connection(self.db_name)
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO logs (mensaje) VALUES (?)",
            (mensaje,),
        )

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
            habitacion = HabitacionFactory.crear_habitacion(
                row["tipo"],
                row["numero"],
            )
            self.habitaciones.append(habitacion)

        def buscar_habitacion(numero):
            return next(
                (h for h in self.habitaciones if h.numero == numero),
                None,
            )

        # Reservas actuales
        cursor.execute(
            "SELECT * FROM reservas "
            "WHERE estado_pila = 'ACTUAL' "
            "ORDER BY id_reserva ASC"
        )

        for reserva in cursor.fetchall():
            habitacion = buscar_habitacion(reserva["numero_habitacion"])
            if habitacion:
                self.pila_reservas_actuales.push(
                    Reserva(
                        reserva["id_reserva"],
                        habitacion,
                        reserva["fecha_inicio"],
                        reserva["fecha_fin"],
                        reserva["cliente"],
                    )
                )

        # Reservas para deshacer
        cursor.execute(
            "SELECT * FROM reservas "
            "WHERE estado_pila = 'DESHACER' "
            "ORDER BY id_reserva ASC"
        )

        for reserva in cursor.fetchall():
            habitacion = buscar_habitacion(reserva["numero_habitacion"])
            if habitacion:
                self.pila_deshacer.push(
                    Reserva(
                        reserva["id_reserva"],
                        habitacion,
                        reserva["fecha_inicio"],
                        reserva["fecha_fin"],
                        reserva["cliente"],
                    )
                )

        conn.close()

    def esta_ocupada(
        self,
        numero_habitacion: int,
        inicio: str,
        fin: str,
    ) -> bool:
        """Verifica si una habitación está ocupada en un rango de fechas."""
        try:
            fecha_inicio = datetime.strptime(inicio, "%Y-%m-%d")
            fecha_fin = datetime.strptime(fin, "%Y-%m-%d")
        except Exception:
            return True

        temp = []
        ocupada = False

        while not self.pila_reservas_actuales.is_empty():
            reserva = self.pila_reservas_actuales.pop()

            if reserva.habitacion.numero == numero_habitacion:
                r_inicio = datetime.strptime(
                    reserva.fecha_inicio,
                    "%Y-%m-%d",
                )
                r_fin = datetime.strptime(
                    reserva.fecha_fin,
                    "%Y-%m-%d",
                )

                if fecha_inicio < r_fin and fecha_fin > r_inicio:
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
                total += habitacion.get_precio_noche(
                    actual.strftime("%Y-%m-%d")
                )
                actual += timedelta(days=1)

            return round(total, 2)

        except Exception:
            return 0.0

    def reservar_habitacion(
        self,
        cliente: str,
        inicio: str,
        fin: str,
        tipo: str = None,
        numero_habitacion: int = None,
    ) -> bool:
        """Realiza una reserva si hay disponibilidad."""
        if inicio >= fin:
            return False

        # Selección de habitación
        if numero_habitacion:
            habitacion = next(
                (h for h in self.habitaciones if h.numero == numero_habitacion),
                None,
            )

            if not habitacion or self.esta_ocupada(
                habitacion.numero,
                inicio,
                fin,
            ):
                return False
        else:
            habitacion = None

            for h in self.habitaciones:
                if (
                    (not tipo or h.tipo == tipo)
                    and not self.esta_ocupada(h.numero, inicio, fin)
                ):
                    habitacion = h
                    break

            if not habitacion:
                return False

        nueva_reserva = Reserva(
            self.contador_reservas,
            habitacion,
            inicio,
            fin,
            cliente,
        )

        self.pila_reservas_actuales.push(nueva_reserva)
        self.contador_reservas += 1

        conn = DatabaseManager.get_connection(self.db_name)
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO reservas VALUES (?, ?, ?, ?, ?, 'ACTUAL')",
            (
                nueva_reserva.id_reserva,
                habitacion.numero,
                inicio,
                fin,
                cliente,
            ),
        )

        conn.commit()
        conn.close()

        self.notificar(
            f"RESERVA: {cliente} | Hab #{habitacion.numero} | "
            f"{inicio} a {fin}"
        )

        return True

    def cancelar_reserva_lifo(self) -> bool:
        """Cancela la última reserva (LIFO)."""
        if self.pila_reservas_actuales.is_empty():
            return False

        reserva = self.pila_reservas_actuales.pop()
        self.pila_deshacer.push(reserva)

        conn = DatabaseManager.get_connection(self.db_name)
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE reservas SET estado_pila='DESHACER' "
            "WHERE id_reserva=?",
            (reserva.id_reserva,),
        )

        conn.commit()
        conn.close()

        self.notificar(
            f"CANCELACIÓN (LIFO): Reserva {reserva.id_reserva} "
            f"de {reserva.cliente}"
        )

        return True

    def borrar_definitivamente_lifo(self) -> bool:
        """Elimina definitivamente una reserva."""
        if self.pila_reservas_actuales.is_empty():
            return False

        reserva = self.pila_reservas_actuales.pop()

        conn = DatabaseManager.get_connection(self.db_name)
        cursor = conn.cursor()

        cursor.execute(
            "DELETE FROM reservas WHERE id_reserva=?",
            (reserva.id_reserva,),
        )

        conn.commit()
        conn.close()

        self.notificar(
            f"BORRADO DEFINITIVO: Reserva {reserva.id_reserva} "
            f"de {reserva.cliente}"
        )

        return True

    def deshacer_cancelacion(self) -> str:
        """Deshace la última cancelación."""
        if self.pila_deshacer.is_empty():
            return "EMPTY"

        reserva = self.pila_deshacer.peek()

        if self.esta_ocupada(
            reserva.habitacion.numero,
            reserva.fecha_inicio,
            reserva.fecha_fin,
        ):
            return "OCCUPIED"

        self.pila_deshacer.pop()
        self.pila_reservas_actuales.push(reserva)

        conn = DatabaseManager.get_connection(self.db_name)
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE reservas SET estado_pila='ACTUAL' "
            "WHERE id_reserva=?",
            (reserva.id_reserva,),
        )

        conn.commit()
        conn.close()

        self.notificar(
            f"DESHACER: Reserva {reserva.id_reserva} "
            f"de {reserva.cliente} restaurada"
        )

        return "OK"

    def obtener_estado_por_rango(self, inicio: str, fin: str):
        """Obtiene disponibilidad y precios por rango."""
        resultado = []

        for habitacion in self.habitaciones:
            datos = habitacion.to_dict()
            datos["disponible"] = not self.esta_ocupada(
                habitacion.numero,
                inicio,
                fin,
            )
            datos["precio_total"] = self.calculate_total_precio(
                habitacion,
                inicio,
                fin,
            )

            resultado.append(datos)

        return resultado

    def buscar_reservas(self, termino: str):
        """Busca reservas por cliente, habitación o fecha."""
        temp = []
        resultados = []

        termino_lower = termino.lower()

        while not self.pila_reservas_actuales.is_empty():
            reserva = self.pila_reservas_actuales.pop()
            match = False

            # Cliente
            if termino_lower in reserva.cliente.lower():
                match = True

            # Número de habitación
            elif termino_lower == str(reserva.habitacion.numero):
                match = True

            else:
                try:
                    fecha = datetime.strptime(termino, "%Y-%m-%d")
                    inicio = datetime.strptime(
                        reserva.fecha_inicio,
                        "%Y-%m-%d",
                    )
                    fin = datetime.strptime(
                        reserva.fecha_fin,
                        "%Y-%m-%d",
                    )

                    if inicio <= fecha < fin:
                        match = True

                except Exception:
                    pass

            if match:
                resultados.append(reserva.to_dict())

            temp.append(reserva)

        for reserva in reversed(temp):
            self.pila_reservas_actuales.push(reserva)

        return resultados

    def obtener_logs(self):
        """Obtiene los últimos logs."""
        conn = DatabaseManager.get_connection(self.db_name)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM logs ORDER BY id DESC LIMIT 15"
        )

        logs = [dict(row) for row in cursor.fetchall()]

        conn.close()

        return logs
