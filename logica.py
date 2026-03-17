from datetime import datetime, timedelta
from database import DatabaseManager
from clases import HabitacionFactory, Reserva, PilaPersonalizada, Sujeto, Observador

# --- Implementación del Observador para Logs ---
class DatabaseLogger(Observador):
    def __init__(self, db_name: str):
        self.db_name = db_name

    def actualizar(self, mensaje: str):
        conn = DatabaseManager.get_connection(self.db_name)
        c = conn.cursor()
        c.execute("INSERT INTO logs (mensaje) VALUES (?)", (mensaje,))
        conn.commit()
        conn.close()

class SistemaReservasHotel(Sujeto):
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

    def obtener_siguiente_id(self):
        conn = DatabaseManager.get_connection(self.db_name)
        c = conn.cursor()
        c.execute("SELECT MAX(id_reserva) FROM reservas")
        max_id = c.fetchone()[0]
        conn.close()
        return (max_id or 0) + 1

    def cargar_datos_desde_bd(self):
        conn = DatabaseManager.get_connection(self.db_name)
        c = conn.cursor()
        self.habitaciones = []
        c.execute("SELECT * FROM habitaciones")
        for row in c.fetchall():
            self.habitaciones.append(HabitacionFactory.crear_habitacion(row['tipo'], row['numero']))

        def buscar_hab_por_num(num):
            return next((h for h in self.habitaciones if h.numero == num), None)

        c.execute("SELECT * FROM reservas WHERE estado_pila = 'ACTUAL' ORDER BY id_reserva ASC")
        for r in c.fetchall():
            hab = buscar_hab_por_num(r['numero_habitacion'])
            if hab: self.pila_reservas_actuales.push(Reserva(r['id_reserva'], hab, r['fecha_inicio'], r['fecha_fin'], r['cliente']))
                
        c.execute("SELECT * FROM reservas WHERE estado_pila = 'DESHACER' ORDER BY id_reserva ASC")
        for r in c.fetchall():
            hab = buscar_hab_por_num(r['numero_habitacion'])
            if hab: self.pila_deshacer.push(Reserva(r['id_reserva'], hab, r['fecha_inicio'], r['fecha_fin'], r['cliente']))
        conn.close()

    def esta_ocupada(self, numero_habitacion: int, inicio: str, fin: str) -> bool:
        try:
            ni = datetime.strptime(inicio, "%Y-%m-%d")
            nf = datetime.strptime(fin, "%Y-%m-%d")
        except: return True

        temp = []
        ocupada = False
        while not self.pila_reservas_actuales.is_empty():
            r = self.pila_reservas_actuales.pop()
            if r.habitacion.numero == numero_habitacion:
                ri = datetime.strptime(r.fecha_inicio, "%Y-%m-%d")
                rf = datetime.strptime(r.fecha_fin, "%Y-%m-%d")
                if ni < rf and nf > ri:
                    ocupada = True
            temp.append(r)
        
        for r in reversed(temp): self.pila_reservas_actuales.push(r)
        return ocupada

    def calculate_total_precio(self, hab, inicio: str, fin: str):
        try:
            curr = datetime.strptime(inicio, "%Y-%m-%d")
            final = datetime.strptime(fin, "%Y-%m-%d")
            total = 0.0
            while curr < final:
                total += hab.get_precio_noche(curr.strftime("%Y-%m-%d"))
                curr += timedelta(days=1)
            return round(total, 2)
        except: return 0.0

    def reservar_habitacion(self, cliente: str, inicio: str, fin: str, tipo: str = None, numero_habitacion: int = None) -> bool:
        if inicio >= fin: return False

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
        c = conn.cursor()
        c.execute("INSERT INTO reservas VALUES (?, ?, ?, ?, ?, 'ACTUAL')", 
                  (nueva.id_reserva, hab.numero, inicio, fin, cliente))
        conn.commit()
        conn.close()
        self.notificar(f"RESERVA: {cliente} | Hab #{hab.numero} | {inicio} a {fin}")
        return True

    def cancelar_reserva_lifo(self) -> bool:
        if self.pila_reservas_actuales.is_empty(): return False
        r = self.pila_reservas_actuales.pop()
        self.pila_deshacer.push(r)
        conn = DatabaseManager.get_connection(self.db_name)
        c = conn.cursor()
        c.execute("UPDATE reservas SET estado_pila='DESHACER' WHERE id_reserva=?", (r.id_reserva,))
        conn.commit()
        conn.close()
        self.notificar(f"CANCELACIÓN (LIFO): Reserva {r.id_reserva} de {r.cliente}")
        return True

    def borrar_definitivamente_lifo(self) -> bool:
        if self.pila_reservas_actuales.is_empty(): return False
        r = self.pila_reservas_actuales.pop()
        conn = DatabaseManager.get_connection(self.db_name)
        c = conn.cursor()
        c.execute("DELETE FROM reservas WHERE id_reserva=?", (r.id_reserva,))
        conn.commit()
        conn.close()
        self.notificar(f"BORRADO DEFINITIVO: Reserva {r.id_reserva} de {r.cliente}")
        return True

    def deshacer_cancelacion(self) -> str:
        if self.pila_deshacer.is_empty(): return "EMPTY"
        r = self.pila_deshacer.peek()
        if self.esta_ocupada(r.habitacion.numero, r.fecha_inicio, r.fecha_fin): return "OCCUPIED"
        
        self.pila_deshacer.pop()
        self.pila_reservas_actuales.push(r)
        conn = DatabaseManager.get_connection(self.db_name)
        c = conn.cursor()
        c.execute("UPDATE reservas SET estado_pila='ACTUAL' WHERE id_reserva=?", (r.id_reserva,))
        conn.commit()
        conn.close()
        self.notificar(f"DESHACER: Reserva {r.id_reserva} de {r.cliente} restaurada")
        return "OK"

    def obtener_estado_por_rango(self, inicio: str, fin: str):
        resultado = []
        for h in self.habitaciones:
            d = h.to_dict()
            d['disponible'] = not self.esta_ocupada(h.numero, inicio, fin)
            d['precio_total'] = self.calculate_total_precio(h, inicio, fin)
            resultado.append(d)
        return resultado

    def buscar_reservas(self, termino: str):
        """Busca en la lista de reservas actuales por cliente, habitación o fecha"""
        temp = []
        resultados = []
        t = termino.lower()
        
        while not self.pila_reservas_actuales.is_empty():
            r = self.pila_reservas_actuales.pop()
            match = False
            # Por cliente
            if t in r.cliente.lower(): match = True
            # Por habitación
            elif t == str(r.habitacion.numero): match = True
            # Por fecha (si el término parece una fecha y está en el rango)
            else:
                try:
                    fecha_busqueda = datetime.strptime(termino, "%Y-%m-%d")
                    ri = datetime.strptime(r.fecha_inicio, "%Y-%m-%d")
                    rf = datetime.strptime(r.fecha_fin, "%Y-%m-%d")
                    if ri <= fecha_busqueda < rf: match = True
                except: pass
            
            if match: resultados.append(r.to_dict())
            temp.append(r)
            
        for r in reversed(temp): self.pila_reservas_actuales.push(r)
        return resultados

    def obtener_logs(self):
        conn = DatabaseManager.get_connection(self.db_name)
        c = conn.cursor()
        c.execute("SELECT * FROM logs ORDER BY id DESC LIMIT 15")
        logs = [dict(row) for row in c.fetchall()]
        conn.close()
        return logs
