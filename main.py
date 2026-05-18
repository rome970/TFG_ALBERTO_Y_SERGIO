from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import requests
import hashlib
import os                     # 👈 Añadido para las variables de entorno
from google import genai      # 👈 Añadido el SDK oficial de Gemini
from dotenv import load_dotenv # 👈 Añadido para cargar el archivo .env

# Cargamos el archivo .env donde guardarás tu clave de Gemini
load_dotenv()

app = FastAPI()

# Inicializamos el cliente oficial de Gemini.
# Busca automáticamente la variable de entorno 'GEMINI_API_KEY'
client = genai.Client()

# TMDB
TMDB_API_KEY = "9862fbf607942773733c0609aad2737f"
BASE_URL = "https://api.themoviedb.org/3"
IMG_URL = "https://image.tmdb.org/t/p/w500"

# SUPABASE
SUPABASE_URL = "https://tdjrikkcwjbbxfflputq.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRkanJpa2tjd2piYnhmZmxwdXRxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzc5MDE5ODUsImV4cCI6MjA5MzQ3Nzk4NX0.Sq3edrEG309qAlvN6SSyAbFZPN4zvIJ3lPCNDYglyMI"

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


class PeliculaCarrito(BaseModel):
    usuario_id: int
    titulo: str
    descripcion: str = "Sin descripción disponible."
    portada: str | None = None
    generos: str = "Sin categoría"
    fecha: str = "Sin fecha"
    puntuacion: float = 0


# 👈 NUEVO: Modelo Pydantic para recibir la consulta de la IA
class ConsultaIA(BaseModel):
    query: str


@app.get("/")
def home():
    return FileResponse("FRONT/main.html")


def hash_password(password: str):
    return hashlib.sha256(password.encode()).hexdigest()


# --- NUEVA RUTA PARA LA BARRA DE BÚSQUEDA CON IA ---
@app.post("/buscar-ia")
def buscar_con_ia(consulta: ConsultaIA):
    if not consulta.query.strip():
        return {"ok": False, "mensaje": "La consulta no puede estar vacía"}

    try:
        # Usamos el modelo rápido y económico gemini-2.5-flash
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=f"Actúa como un recomendador experto en cine y asistente para mi web de películas. Responde de forma amigable y concisa: {consulta.query}"
        )
        
        return {
            "ok": True,
            "resultado": response.text
        }
    except Exception as e:
        return {
            "ok": False,
            "mensaje": "Error al conectar con el servicio de IA",
            "error": str(e)
        }


@app.post("/registro")
def registro(usuario: RegistroUsuario):
    comprobar = requests.get(
        f"{SUPABASE_URL}/rest/v1/usuarios",
        headers=SUPABASE_HEADERS,
        params={
            "email": f"eq.{usuario.email}",
            "select": "id,nombre,email"
        }
    )

    if comprobar.status_code != 200:
        return {
            "ok": False,
            "mensaje": "Error comprobando usuario",
            "error": comprobar.text
        }

    if len(comprobar.json()) > 0:
        return {
            "ok": False,
            "mensaje": "Ese email ya está registrado"
        }

    respuesta = requests.post(
        f"{SUPABASE_URL}/rest/v1/usuarios",
        headers=SUPABASE_HEADERS,
        json={
            "nombre": usuario.nombre,
            "email": usuario.email,
            "password": hash_password(usuario.password)
        }
    )

    if respuesta.status_code not in [200, 201]:
        return {
            "ok": False,
            "mensaje": "Error al registrar usuario",
            "error": respuesta.text
        }

    buscar_usuario = requests.get(
        f"{SUPABASE_URL}/rest/v1/usuarios",
        headers=SUPABASE_HEADERS,
        params={
            "email": f"eq.{usuario.email}",
            "select": "id,nombre,email"
        }
    )

    datos_usuario = buscar_usuario.json()

    if len(datos_usuario) == 0:
        return {
            "ok": False,
            "mensaje": "Usuario creado, pero no se pudo recuperar su ID"
        }

    return {
        "ok": True,
        "mensaje": "Usuario registrado correctamente",
        "usuario": datos_usuario[0]
    }


@app.post("/login")
def login(usuario: LoginUsuario):
    respuesta = requests.get(
        f"{SUPABASE_URL}/rest/v1/usuarios",
        headers=SUPABASE_HEADERS,
        params={
            "email": f"eq.{usuario.email}",
            "password": f"eq.{hash_password(usuario.password)}",
            "select": "id,nombre,email"
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
        return {
            "ok": False,
            "mensaje": "Email o contraseña incorrectos"
        }

    return {
        "ok": True,
        "mensaje": "Login correcto",
        "usuario": datos[0]
    }


@app.post("/carrito/agregar")
def agregar_carrito(pelicula: PeliculaCarrito):
    datos = {
        "usuario_id": pelicula.usuario_id,
        "titulo": pelicula.titulo,
        "descripcion": pelicula.descripcion,
        "portada": pelicula.portada,
        "generos": pelicula.generos,
        "fecha": pelicula.fecha,
        "puntuacion": pelicula.puntuacion
    }

    respuesta = requests.post(
        f"{SUPABASE_URL}/rest/v1/carrito",
        headers=SUPABASE_HEADERS,
        json=datos
    )

    if respuesta.status_code in [200, 201]:
        return {
            "ok": True,
            "mensaje": "Película guardada en el carrito"
        }

    return {
        "ok": False,
        "mensaje": "Error al guardar película",
        "error": respuesta.text
    }


@app.get("/carrito")
def ver_carrito(usuario_id: int = Query(...)):
    respuesta = requests.get(
        f"{SUPABASE_URL}/rest/v1/carrito",
        headers=SUPABASE_HEADERS,
        params={
            "usuario_id": f"eq.{usuario_id}",
            "select": "*",
            "order": "id.desc"
        }
    )

    if respuesta.status_code != 200:
        return {
            "ok": False,
            "mensaje": "Error al cargar carrito",
            "error": respuesta.text,
            "peliculas": []
        }

    return {
        "ok": True,
        "peliculas": respuesta.json()
    }


@app.delete("/carrito/eliminar/{id_pelicula}")
def eliminar_carrito(id_pelicula: int):
    respuesta = requests.delete(
        f"{SUPABASE_URL}/rest/v1/carrito",
        headers=SUPABASE_HEADERS,
        params={
            "id": f"eq.{id_pelicula}"
        }
    )

    if respuesta.status_code in [200, 204]:
        return {
            "ok": True,
            "mensaje": "Película eliminada"
        }

    return {
        "ok": False,
        "mensaje": "Error al eliminar película",
        "error": respuesta.text
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

    return {
        g["id"]: g["name"] for g in generos
    }


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