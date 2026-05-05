from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import requests
import hashlib

app = FastAPI()

# TMDB
TMDB_API_KEY = "9862fbf607942773733c0609aad2737f"
BASE_URL = "https://api.themoviedb.org/3"
IMG_URL = "https://image.tmdb.org/t/p/w500"

# SUPABASE
SUPABASE_URL = "https://tdjrikkcwjbbxfflputq.supabase.co"
SUPABASE_KEY = "sb_publishable_iIhqbP5dbFtInuPrqqJNRQ_19ojgHPY"

SUPABASE_HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

app.mount("/front", StaticFiles(directory="FRONT"), name="front")
app.mount("/imagenes", StaticFiles(directory="IMAGENES"), name="imagenes")


class RegistroUsuario(BaseModel):
    nombre: str
    email: str
    password: str


class LoginUsuario(BaseModel):
    email: str
    password: str


@app.get("/")
def home():
    return FileResponse("FRONT/main.html")


def hash_password(password: str):
    return hashlib.sha256(password.encode()).hexdigest()


@app.post("/registro")
def registro(usuario: RegistroUsuario):
    comprobar = requests.get(
        f"{SUPABASE_URL}/rest/v1/usuarios",
        headers=SUPABASE_HEADERS,
        params={
            "email": f"eq.{usuario.email}",
            "select": "email"
        }
    )

    if comprobar.status_code == 200 and len(comprobar.json()) > 0:
        return {"ok": False, "mensaje": "Ese email ya está registrado"}

    respuesta = requests.post(
        f"{SUPABASE_URL}/rest/v1/usuarios",
        headers=SUPABASE_HEADERS,
        json={
            "nombre": usuario.nombre,
            "email": usuario.email,
            "password": hash_password(usuario.password)
        }
    )

    if respuesta.status_code in [200, 201]:
        return {
            "ok": True,
            "mensaje": "Usuario registrado correctamente",
            "usuario": {
                "nombre": usuario.nombre,
                "email": usuario.email
            }
        }

    return {
        "ok": False,
        "mensaje": "Error al registrar usuario",
        "error": respuesta.text
    }


@app.post("/login")
def login(usuario: LoginUsuario):
    respuesta = requests.get(
        f"{SUPABASE_URL}/rest/v1/usuarios",
        headers=SUPABASE_HEADERS,
        params={
            "email": f"eq.{usuario.email}",
            "password": f"eq.{hash_password(usuario.password)}",
            "select": "nombre,email"
        }
    )

    if respuesta.status_code != 200:
        return {
            "ok": False,
            "mensaje": "Error conectando con Supabase",
            "error": respuesta.text
        }

    datos = respuesta.json()

    if len(datos) == 0:
        return {"ok": False, "mensaje": "Email o contraseña incorrectos"}

    return {
        "ok": True,
        "mensaje": "Login correcto",
        "usuario": datos[0]
    }


def obtener_generos():
    respuesta = requests.get(
        f"{BASE_URL}/genre/movie/list",
        params={
            "language": "es-ES",
            "api_key": TMDB_API_KEY
        }
    )

    generos = respuesta.json().get("genres", [])
    return {g["id"]: g["name"] for g in generos}


def formatear_peliculas(peliculas, mapa_generos):
    resultado = []

    for pelicula in peliculas:
        resultado.append({
            "titulo": pelicula.get("title"),
            "descripcion": pelicula.get("overview") or "Sin descripción disponible.",
            "portada": IMG_URL + pelicula["poster_path"] if pelicula.get("poster_path") else None,
            "generos": [
                mapa_generos.get(id_genero, "Desconocido")
                for id_genero in pelicula.get("genre_ids", [])
            ],
            "fecha": pelicula.get("release_date") or "Sin fecha",
            "puntuacion": pelicula.get("vote_average") or 0
        })

    return resultado


@app.get("/peliculas-populares")
def peliculas_populares():
    respuesta = requests.get(
        f"{BASE_URL}/movie/popular",
        params={
            "language": "es-ES",
            "api_key": TMDB_API_KEY,
            "page": 1
        }
    )

    peliculas = respuesta.json().get("results", [])
    mapa_generos = obtener_generos()

    return formatear_peliculas(peliculas, mapa_generos)


@app.get("/buscar-basico")
def buscar(peli: str = Query(...)):
    respuesta = requests.get(
        f"{BASE_URL}/search/movie",
        params={
            "query": peli,
            "language": "es-ES",
            "api_key": TMDB_API_KEY
        }
    )

    peliculas = respuesta.json().get("results", [])
    mapa_generos = obtener_generos()

    return formatear_peliculas(peliculas, mapa_generos)