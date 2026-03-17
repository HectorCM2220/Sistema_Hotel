import os
import sqlite3


class DatabaseManager:
    """Gestor de conexiones y configuración de la base de datos."""

    @staticmethod
    def get_connection(db_name: str = "hotel.db"):
        """Crea y retorna una conexión a la base de datos."""
        conn = sqlite3.connect(db_name)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def setup(db_name: str = "hotel.db"):
        """Inicializa la base de datos y crea tablas si no existen."""
        conn = DatabaseManager.get_connection(db_name)
        cursor = conn.cursor()

        # Tabla de habitaciones
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS habitaciones (
                numero INTEGER PRIMARY KEY,
                tipo TEXT,
                precio_base REAL
            )
            """
        )

        # Validación de migración:
        # Si existe la columna antigua 'fecha', eliminamos la tabla
        cursor.execute("PRAGMA table_info(reservas)")
        columnas = [row["name"] for row in cursor.fetchall()]

        if "fecha" in columnas:
            cursor.execute("DROP TABLE reservas")

        # Tabla de reservas
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS reservas (
                id_reserva INTEGER PRIMARY KEY,
                numero_habitacion INTEGER,
                fecha_inicio TEXT,
                fecha_fin TEXT,
                cliente TEXT,
                estado_pila TEXT
            )
            """
        )

        # Tabla de logs
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mensaje TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # Insertar habitaciones iniciales si la tabla está vacía
        cursor.execute("SELECT COUNT(*) FROM habitaciones")

        if cursor.fetchone()[0] == 0:
            habitaciones = []

            # Habitaciones simples
            for i in range(1, 11):
                habitaciones.append((101 + i, "Simple", 50.0))

            # Habitaciones dobles
            for i in range(1, 9):
                habitaciones.append((201 + i, "Doble", 85.0))

            # Suites
            for i in range(1, 7):
                habitaciones.append((301 + i, "Suite", 150.0))

            cursor.executemany(
                "INSERT INTO habitaciones VALUES (?, ?, ?)",
                habitaciones,
            )

        conn.commit()
        conn.close()
