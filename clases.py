from datetime import datetime


class Observador:
    """Interfaz base para observadores."""

    def actualizar(self, mensaje: str) -> None:
        """Recibe una notificación con un mensaje."""
        pass


class Sujeto:
    """Clase base que implementa el patrón Observador."""

    def __init__(self):
        self._observadores = []

    def agregar_observador(self, observador: Observador) -> None:
        """Agrega un observador a la lista."""
        self._observadores.append(observador)

    def notificar(self, mensaje: str) -> None:
        """Notifica a todos los observadores."""
        for observador in self._observadores:
            observador.actualizar(mensaje)


class PilaPersonalizada:
    """Implementación de una pila con capacidad limitada."""

    def __init__(self, capacidad_maxima: int):
        self.elementos = []
        self.capacidad_maxima = capacidad_maxima

    def push(self, elemento) -> None:
        """Agrega un elemento a la pila."""
        if self.is_full():
            raise OverflowError("Pila llena.")
        self.elementos.append(elemento)

    def pop(self):
        """Elimina y retorna el elemento superior."""
        if self.is_empty():
            raise IndexError("Pila vacía.")
        return self.elementos.pop()

    def peek(self):
        """Retorna el elemento superior sin eliminarlo."""
        if self.is_empty():
            raise IndexError("Pila vacía.")
        return self.elementos[-1]

    def is_empty(self) -> bool:
        """Verifica si la pila está vacía."""
        return len(self.elementos) == 0

    def is_full(self) -> bool:
        """Verifica si la pila está llena."""
        return len(self.elementos) >= self.capacidad_maxima

    def size(self) -> int:
        """Retorna el número de elementos en la pila."""
        return len(self.elementos)


# --- Modelos con Precio ---
class Habitacion:
    """Clase base para representar una habitación."""

    def __init__(self, numero: int, tipo: str, precio_base: float):
        self.numero = numero
        self.tipo = tipo
        self.precio_base = precio_base

    def get_precio_noche(self, fecha_str: str) -> float:
        """
        Calcula el precio por noche basado en reglas dinámicas:
        - Invierno: descuento
        - Lunes: descuento
        - Fin de semana: recargo
        """
        try:
            fecha = datetime.strptime(fecha_str, "%Y-%m-%d")
            precio = self.precio_base

            # Temporada de invierno
            if fecha.month in [12, 1, 2]:
                precio *= 0.85

            # Ajustes por día de la semana
            if fecha.weekday() == 0:  # Lunes
                precio *= 0.90
            elif fecha.weekday() >= 5:  # Sábado o domingo
                precio *= 1.20

            return round(precio, 2)

        except Exception:
            return self.precio_base

    def to_dict(self) -> dict:
        """Convierte la habitación a diccionario."""
        return {
            "numero": self.numero,
            "tipo": self.tipo,
            "precio_base": self.precio_base,
        }


class HabitacionSimple(Habitacion):
    """Habitación tipo simple."""

    def __init__(self, numero: int):
        super().__init__(numero, "Simple", 50.0)


class HabitacionDoble(Habitacion):
    """Habitación tipo doble."""

    def __init__(self, numero: int):
        super().__init__(numero, "Doble", 85.0)


class HabitacionSuite(Habitacion):
    """Habitación tipo suite."""

    def __init__(self, numero: int):
        super().__init__(numero, "Suite", 150.0)


# --- Patrón Factory ---
class HabitacionFactory:
    """Factory para crear habitaciones según su tipo."""

    @staticmethod
    def crear_habitacion(tipo: str, numero: int) -> Habitacion:
        """Crea una instancia de habitación según el tipo."""
        if tipo == "Simple":
            return HabitacionSimple(numero)

        if tipo == "Doble":
            return HabitacionDoble(numero)

        if tipo == "Suite":
            return HabitacionSuite(numero)

        raise ValueError(f"Tipo desconocido: {tipo}")


class Reserva:
    """Representa una reserva de hotel."""

    def __init__(
        self,
        id_reserva: int,
        habitacion: Habitacion,
        fecha_inicio: str,
        fecha_fin: str,
        cliente: str,
    ):
        self.id_reserva = id_reserva
        self.habitacion = habitacion
        self.fecha_inicio = fecha_inicio
        self.fecha_fin = fecha_fin
        self.cliente = cliente

    def to_dict(self) -> dict:
        """Convierte la reserva a diccionario."""
        return {
            "id_reserva": self.id_reserva,
            "habitacion": self.habitacion.to_dict(),
            "fecha_inicio": self.fecha_inicio,
            "fecha_fin": self.fecha_fin,
            "cliente": self.cliente,
        }
