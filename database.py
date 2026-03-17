import sqlite3
import os

class DatabaseManager:
    @staticmethod
    def get_connection(db_name='hotel.db'):
        conn = sqlite3.connect(db_name)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def setup(db_name='hotel.db'):
        conn = DatabaseManager.get_connection(db_name)
        c = conn.cursor()
        
        c.execute('''CREATE TABLE IF NOT EXISTS habitaciones (
            numero INTEGER PRIMARY KEY, tipo TEXT, precio_base REAL)''')
        
        # Validación de Migración: Si existe la columna 'fecha' antigua, borramos la tabla
        c.execute("PRAGMA table_info(reservas)")
        columnas = [row['name'] for row in c.fetchall()]
        if "fecha" in columnas:
            c.execute("DROP TABLE reservas")

        c.execute('''CREATE TABLE IF NOT EXISTS reservas (
            id_reserva INTEGER PRIMARY KEY, numero_habitacion INTEGER,
            fecha_inicio TEXT, fecha_fin TEXT, cliente TEXT, estado_pila TEXT)''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            mensaje TEXT, 
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
        
        c.execute('SELECT COUNT(*) FROM habitaciones')
        if c.fetchone()[0] == 0:
            habitaciones = []
            # Usaremos los precios base definidos en las clases
            for i in range(1, 11): habitaciones.append((101 + i, "Simple", 50.0))
            for i in range(1, 9): habitaciones.append((201 + i, "Doble", 85.0))
            for i in range(1, 7): habitaciones.append((301 + i, "Suite", 150.0))
            
            c.executemany("INSERT INTO habitaciones VALUES (?, ?, ?)", habitaciones)
        
        conn.commit()
        conn.close()


