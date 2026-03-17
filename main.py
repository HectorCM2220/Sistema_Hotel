from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from datetime import datetime
import uvicorn
import os

from logica import SistemaReservasHotel

app = FastAPI(title="Practica Hotel")

if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

hotel = SistemaReservasHotel(db_name="hotel_web.db")

@app.get("/")
async def read_index():
    return FileResponse("static/index.html")

@app.get("/api/estado")
async def get_estado(inicio: str = None, fin: str = None):
    hoy = datetime.now()
    if not inicio: inicio = hoy.strftime("%Y-%m-%d")
    if not fin: fin = (hoy + timedelta(days=1)).strftime("%Y-%m-%d")
    
    reservas = []
    temp = []
    while not hotel.pila_reservas_actuales.is_empty():
        r = hotel.pila_reservas_actuales.pop()
        reservas.append(r.to_dict())
        temp.append(r)
    for r in reversed(temp): hotel.pila_reservas_actuales.push(r)

    return {
        "habitaciones": hotel.obtener_estado_por_rango(inicio, fin),
        "reservas": reservas,
        "logs": hotel.obtener_logs(),
        "deshacer_count": hotel.pila_deshacer.size()
    }

@app.get("/api/buscar")
async def buscar(query: str):
    return hotel.buscar_reservas(query)

@app.post("/api/reservar")
async def reservar(cliente: str = Form(...), inicio: str = Form(...), fin: str = Form(...), 
                   tipo: str = Form(None), numero_habitacion: int = Form(None)):
    if tipo == "Cualquiera" or not tipo: tipo = None
    if hotel.reservar_habitacion(cliente, inicio, fin, tipo, numero_habitacion):
        return {"status": "success", "message": f"Reserva para {cliente} completada."}
    raise HTTPException(status_code=400, detail="No disponible en esas fechas o tipo.")

@app.post("/api/cancelar/lifo")
async def cancelar_lifo():
    if hotel.cancelar_reserva_lifo():
        return {"status": "success", "message": "Última reserva enviada a la papelera."}
    raise HTTPException(status_code=400, detail="Nada que cancelar.")

@app.post("/api/borrar_definitivo")
async def borrar_definitivo():
    if hotel.borrar_definitivamente_lifo():
        return {"status": "success", "message": "Reserva eliminada permanentemente."}
    raise HTTPException(status_code=400, detail="Nada que borrar.")

@app.post("/api/deshacer")
async def deshacer():
    st = hotel.deshacer_cancelacion()
    if st == "OK": return {"status": "success", "message": "Acción deshecha."}
    elif st == "OCCUPIED": raise HTTPException(status_code=400, detail="Habitación ya ocupada en ese rango.")
    raise HTTPException(status_code=400, detail="Nada que deshacer.")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
