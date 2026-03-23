from datetime import datetime, timedelta
import os

import uvicorn
from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from logica import SistemaReservasHotel


app = FastAPI(title="Practica Hotel")

# Configuración de la base de datos para Vercel (read-only filesystem except /tmp)
DB_PATH = os.environ.get("DB_PATH", "hotel_web.db")

# Crear carpeta static si no existe (silenciosamente)
try:
    if not os.path.exists("static"):
        os.makedirs("static")
except Exception:
    pass

app.mount("/static", StaticFiles(directory="static"), name="static")

hotel = SistemaReservasHotel(db_name=DB_PATH)


@app.get("/")
async def read_index():
    """Devuelve la página principal."""
    return FileResponse("static/index.html")


@app.get("/api/estado")
async def get_estado(inicio: str = None, fin: str = None):
    """
    Obtiene el estado del hotel en un rango de fechas.
    """
    hoy = datetime.now()

    if not inicio:
        inicio = hoy.strftime("%Y-%m-%d")

    if not fin:
        fin = (hoy + timedelta(days=1)).strftime("%Y-%m-%d")

    reservas = []
    temp = []

    # Extraer reservas de la pila
    while not hotel.pila_reservas_actuales.is_empty():
        reserva = hotel.pila_reservas_actuales.pop()
        reservas.append(reserva.to_dict())
        temp.append(reserva)

    # Restaurar la pila
    for reserva in reversed(temp):
        hotel.pila_reservas_actuales.push(reserva)

    return {
        "habitaciones": hotel.obtener_estado_por_rango(inicio, fin),
        "reservas": reservas,
        "logs": hotel.obtener_logs(),
        "deshacer_count": hotel.pila_deshacer.size(),
    }


@app.get("/api/buscar")
async def buscar(query: str):
    """Busca reservas según un criterio."""
    return hotel.buscar_reservas(query)


@app.post("/api/reservar")
async def reservar(
    cliente: str = Form(...),
    inicio: str = Form(...),
    fin: str = Form(...),
    tipo: str = Form(None),
    numero_habitacion: int = Form(None),
):
    """
    Realiza una reserva de habitación.
    """
    if tipo == "Cualquiera" or not tipo:
        tipo = None

    success = hotel.reservar_habitacion(
        cliente,
        inicio,
        fin,
        tipo,
        numero_habitacion,
    )

    if success:
        return {
            "status": "success",
            "message": f"Reserva para {cliente} completada.",
        }

    raise HTTPException(
        status_code=400,
        detail="No disponible en esas fechas o tipo.",
    )


@app.post("/api/cancelar/lifo")
async def cancelar_lifo():
    """Cancela la última reserva (LIFO)."""
    if hotel.cancelar_reserva_lifo():
        return {
            "status": "success",
            "message": "Última reserva enviada a la papelera.",
        }

    raise HTTPException(
        status_code=400,
        detail="Nada que cancelar.",
    )


@app.post("/api/borrar_definitivo")
async def borrar_definitivo():
    """Elimina definitivamente la última reserva cancelada."""
    if hotel.borrar_definitivamente_lifo():
        return {
            "status": "success",
            "message": "Reserva eliminada permanentemente.",
        }

    raise HTTPException(
        status_code=400,
        detail="Nada que borrar.",
    )


@app.post("/api/deshacer")
async def deshacer():
    """Deshace la última cancelación."""
    estado = hotel.deshacer_cancelacion()

    if estado == "OK":
        return {
            "status": "success",
            "message": "Acción deshecha.",
        }

    if estado == "OCCUPIED":
        raise HTTPException(
            status_code=400,
            detail="Habitación ya ocupada en ese rango.",
        )

    raise HTTPException(
        status_code=400,
        detail="Nada que deshacer.",
    )


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
