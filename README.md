# Sistema de Reservas de Hotel

## Integrantes

* Ceja Cervantes Alejandro
* Covarrubias Martínez Hector
* Escobar Rubio Dominic

## Descripción

Este proyecto es una aplicación web para la gestión de reservas de un hotel. Está desarrollada con FastAPI y utiliza SQLite como base de datos.

El objetivo principal es implementar un sistema funcional que permita administrar reservas, aplicando conceptos como estructuras de datos (pilas), persistencia en base de datos y el patrón de diseño observador.

---

## Características principales

* Reservar habitaciones por rango de fechas
* Buscar reservas por cliente, número de habitación o fecha
* Cancelar reservas utilizando lógica LIFO (última en entrar, primera en salir)
* Deshacer cancelaciones
* Eliminar reservas de forma definitiva
* Consultar el estado del hotel en tiempo real
* Registrar acciones mediante un sistema de logs

---

### Estructuras de datos

* Uso de una pila personalizada para:

  * Reservas actuales
  * Historial de deshacer

### Patrón Observador

* Registro automático de eventos del sistema
* Implementación mediante un observador que guarda logs en la base de datos

### Persistencia

* Uso de SQLite para almacenar:

  * Habitaciones
  * Reservas
  * Logs

---

## Estructura del proyecto

```id="stc001"
.
├── main.py              # API con FastAPI
├── logica.py            # Lógica del sistema de reservas
├── database.py          # Configuración de base de datos
├── clases.py            # Modelos y estructuras
├── static/              # Archivos del frontend
└── hotel_web.db         # Base de datos SQLite
```

---

## Instalación y ejecución

### Clonar el repositorio

```bash id="stc002"
git clone <tu-repo>
cd <tu-repo>
```

### Instalar dependencias

```bash id="stc003"
pip install fastapi uvicorn
```

### Ejecutar el servidor

```bash id="stc004"
python main.py
```

O con uvicorn:

```bash id="stc005"
uvicorn main:app --reload
```

### Acceso en navegador

```id="stc006"
http://127.0.0.1:8000
```

---

## Endpoints principales

* GET /api/estado
* GET /api/buscar?query=valor
* POST /api/reservar
* POST /api/cancelar/lifo
* POST /api/deshacer
* POST /api/borrar_definitivo

---

## Notas importantes

* El sistema utiliza una estructura tipo pila, por lo que la última reserva realizada es la primera en cancelarse
* Se validan automáticamente conflictos de fechas
* El cálculo de precios se realiza en función del número de días de estancia

---

## Posibles mejoras

* Implementar autenticación de usuarios
* Migrar a un ORM como SQLAlchemy
* Desarrollar un frontend más avanzado
* Mejorar validaciones con Pydantic
* Soporte para múltiples hoteles
