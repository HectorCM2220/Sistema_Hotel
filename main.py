from datetime import datetime


class PilaPersonalizada:
    """Implementación de una pila con capacidad limitada."""

    def __init__(self, capacidad=100):
        self.capacidad = capacidad
        self._datos = []

    def push(self, item):
        if self.is_full():
            raise OverflowError("Pila llena")
        self._datos.append(item)

    def pop(self):
        if self.is_empty():
            raise IndexError("Pila vacía")
        return self._datos.pop()

    def peek(self):
        if self.is_empty():
            raise IndexError("Pila vacía")
        return self._datos[-1]

    def is_empty(self):
        return len(self._datos) == 0

    def is_full(self):
        return len(self._datos) >= self.capacidad

    def size(self):
        return len(self._datos)


class Reserva:
    """Representa una reserva de hotel."""

    def __init__(self, reserva_id, cliente, inicio, fin, habitacion, tipo):
        self.reserva_id = reserva_id
        self.cliente = cliente
        self.inicio = inicio
        self.fin = fin
        self.habitacion = habitacion
        self.tipo = tipo

    def to_dict(self):
        return {
            "id": self.reserva_id,
            "cliente": self.cliente,
            "inicio": self.inicio,
            "fin": self.fin,
            "habitacion": self.habitacion,
            "tipo": self.tipo,
        }


class SistemaReservasHotel:
    """Sistema de gestión de reservas con soporte LIFO y deshacer."""

    def __init__(self, db_name=None):
        self.contador_reservas = 1
        self.habitaciones = [
            {"numero": 1, "tipo": "Simple"},
            {"numero": 2, "tipo": "Simple"},
            {"numero": 3, "tipo": "Doble"},
            {"numero": 4, "tipo": "Doble"},
            {"numero": 5, "tipo": "Suite"},
            {"numero": 6, "tipo": "Suite"},
        ]
        self.pila_reservas_actuales = PilaPersonalizada()
        self.pila_deshacer = PilaPersonalizada()
        self.logs = []

    def _fecha_valida(self, fecha):
        try:
            return datetime.strptime(fecha, "%Y-%m-%d")
        except Exception:
            return None

    def _habitacion_disponible(self, inicio, fin, tipo=None, numero=None):
        inicio_dt = self._fecha_valida(inicio)
        fin_dt = self._fecha_valida(fin)

        if not inicio_dt or not fin_dt:
            return None

        ocupadas = []
        temp = []

        while not self.pila_reservas_actuales.is_empty():
            r = self.pila_reservas_actuales.pop()
            temp.append(r)

            r_inicio = self._fecha_valida(r.inicio)
            r_fin = self._fecha_valida(r.fin)

            if not (fin_dt <= r_inicio or inicio_dt >= r_fin):
                ocupadas.append(r.habitacion)

        for r in reversed(temp):
            self.pila_reservas_actuales.push(r)

        for h in self.habitaciones:
            if numero and h["numero"] != numero:
                continue
            if tipo and h["tipo"] != tipo:
                continue
            if h["numero"] not in ocupadas:
                return h

        return None

    def reservar_habitacion(self, cliente, inicio, fin=None, tipo=None, numero=None):
        if not fin:
            fin = inicio

        if not self._fecha_valida(inicio) or not self._fecha_valida(fin):
            return False

        habitacion = self._habitacion_disponible(inicio, fin, tipo, numero)

        if not habitacion:
            return False

        reserva = Reserva(
            self.contador_reservas,
            cliente,
            inicio,
            fin,
            habitacion["numero"],
            habitacion["tipo"],
        )

        self.pila_reservas_actuales.push(reserva)
        self.logs.append(f"Reserva creada: {reserva.reserva_id}")
        self.contador_reservas += 1

        return True

    def cancelar_reserva(self, reserva_id):
        temp = []
        encontrada = None

        while not self.pila_reservas_actuales.is_empty():
            r = self.pila_reservas_actuales.pop()
            if r.reserva_id == reserva_id:
                encontrada = r
                break
            temp.append(r)

        for r in reversed(temp):
            self.pila_reservas_actuales.push(r)

        if not encontrada:
            return False

        self.pila_deshacer.push(encontrada)
        self.logs.append(f"Reserva cancelada: {reserva_id}")
        return True

    def cancelar_reserva_lifo(self):
        if self.pila_reservas_actuales.is_empty():
            return False

        r = self.pila_reservas_actuales.pop()
        self.pila_deshacer.push(r)
        self.logs.append(f"Cancelación LIFO: {r.reserva_id}")
        return True

    def borrar_definitivamente_lifo(self):
        if self.pila_deshacer.is_empty():
            return False

        r = self.pila_deshacer.pop()
        self.logs.append(f"Borrado definitivo: {r.reserva_id}")
        return True

    def deshacer_cancelacion(self):
        if self.pila_deshacer.is_empty():
            return "EMPTY"

        r = self.pila_deshacer.peek()

        disponible = self._habitacion_disponible(
            r.inicio, r.fin, r.tipo, r.habitacion
        )

        if not disponible:
            return "OCCUPIED"

        r = self.pila_deshacer.pop()
        self.pila_reservas_actuales.push(r)
        self.logs.append(f"Deshacer cancelación: {r.reserva_id}")
        return "OK"

    def obtener_estado_por_rango(self, inicio, fin):
        resultado = []

        for h in self.habitaciones:
            resultado.append(
                {
                    "numero": h["numero"],
                    "tipo": h["tipo"],
                    "ocupada": False,
                }
            )

        temp = []

        while not self.pila_reservas_actuales.is_empty():
            r = self.pila_reservas_actuales.pop()
            temp.append(r)

            for h in resultado:
                if h["numero"] == r.habitacion:
                    h["ocupada"] = True

        for r in reversed(temp):
            self.pila_reservas_actuales.push(r)

        return resultado

    def buscar_reservas(self, query):
        resultados = []
        temp = []

        while not self.pila_reservas_actuales.is_empty():
            r = self.pila_reservas_actuales.pop()
            temp.append(r)

            if (
                query.lower() in r.cliente.lower()
                or query == str(r.reserva_id)
            ):
                resultados.append(r.to_dict())

        for r in reversed(temp):
            self.pila_reservas_actuales.push(r)

        return resultados

    def obtener_logs(self):
        return self.logs
