from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}

#Ruta para obtener un saludo
@app.get("/saludo/{nombre}")

def obtener_saludo(nombre: str):
    return {"message": f"Hola {nombre}"}

    participantes = []

@app.get("/participantes")
def listar_participantes() -> list[dict[str,str]]:
    return participantes  