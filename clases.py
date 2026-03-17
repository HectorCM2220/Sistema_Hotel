# --- Patrón Observer ---
class Observador:
    def actualizar(self, mensaje: str): pass

class Sujeto:
    def __init__(self): self._observadores = []
    def agregar_observador(self, obs: Observador): self._observadores.append(obs)
    def notificar(self, mensaje: str):
        for obs in self._observadores: obs.actualizar(mensaje)

class PilaPersonalizada:
    def __init__(self, capacidad_maxima: int):
        self.elementos = []
        self.capacidad_maxima = capacidad_maxima

    def push(self, elemento) -> None:
        if self.is_full():
            raise OverflowError("Pila llena.")
        self.elementos.append(elemento)

    def pop(self):
        if self.is_empty():
            raise IndexError("Pila vacía.")
        return self.elementos.pop()

    def peek(self):
        if self.is_empty():
            raise IndexError("Pila vacía.")
        return self.elementos[-1]

    def is_empty(self) -> bool:
        return len(self.elementos) == 0

    def is_full(self) -> bool:
        return len(self.elementos) >= self.capacidad_maxima

    def size(self) -> int:
        return len(self.elementos)


# --- Modelos con Precio ---
class Habitacion:
    def __init__(self, numero: int, tipo: str, precio_base: float):
        self.numero = numero
        self.tipo = tipo
        self.precio_base = precio_base

    def get_precio_noche(self, fecha_str: str) -> float:
        # Lógica de precio dinámico
        from datetime import datetime
        try:
            dt = datetime.strptime(fecha_str, "%Y-%m-%d")
            precio = self.precio_base

            # 1. Temporada de Invierno (Dic, Ene, Feb): -15%
            if dt.month in [12, 1, 2]:
                precio *= 0.85

            # 2. Ajustes Semanales
            if dt.weekday() == 0: # Lunes: -10%
                precio *= 0.90
            elif dt.weekday() >= 5: # Sáb o Dom: +20%
                precio *= 1.20

            return round(precio, 2)
        except: pass
        return self.precio_base

    def to_dict(self):
        return {
            "numero": self.numero,
            "tipo": self.tipo,
            "precio_base": self.precio_base
        }

class HabitacionSimple(Habitacion):
    def __init__(self, numero: int): super().__init__(numero, "Simple", 50.0)

class HabitacionDoble(Habitacion):
    def __init__(self, numero: int): super().__init__(numero, "Doble", 85.0)

class HabitacionSuite(Habitacion):
    def __init__(self, numero: int): super().__init__(numero, "Suite", 150.0)

# --- Patrón Factory ---
class HabitacionFactory:
    @staticmethod
    def crear_habitacion(tipo: str, numero: int) -> Habitacion:
        if tipo == "Simple": return HabitacionSimple(numero)
        elif tipo == "Doble": return HabitacionDoble(numero)
        elif tipo == "Suite": return HabitacionSuite(numero)
        raise ValueError(f"Tipo desconocido: {tipo}")

class Reserva:
    def __init__(self, id_reserva: int, habitacion: Habitacion, fecha_inicio: str, fecha_fin: str, cliente: str):
        self.id_reserva = id_reserva
        self.habitacion = habitacion
        self.fecha_inicio = fecha_inicio
        self.fecha_fin = fecha_fin
        self.cliente = cliente

    def to_dict(self):
        return {
            "id_reserva": self.id_reserva,
            "habitacion": self.habitacion.to_dict(),
            "fecha_inicio": self.fecha_inicio,
            "fecha_fin": self.fecha_fin,
            "cliente": self.cliente
        }
