from fastapi import FastAPI
import requests
import os

app = FastAPI()
    # Clave API de la base de datos externa
TMDB_API_KEY = "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJhY2NkNTQ5ZDQ1NjE3YWUzNDM4NmRlYjM5M2EzMmI5YyIsIm5iZiI6MTc3NjA5NDk5Ny44OTIsInN1YiI6IjY5ZGQwZjE1ODRhMjkyNWUxN2M3MzYzOSIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.hY4irC3xKSDkRlAM5g40iu7HB5hz8qLl0QktsryrJdk"
BASE_URL = "https://api.themoviedb.org/3"


@app.get("/")
def home():
    return {"mensaje": "Servidor del TFG funcionando perfectamente"}

@app.get("/buscar-basico")
def buscar(peli: str):
    url = f"{BASE_URL}/search/movie?query={peli}&language=es-ES"
    
    headers = {
        "Authorization": f"Bearer {TMDB_API_KEY}",
        "accept": "application/json"
    }
    
    respuesta = requests.get(url, headers=headers)
    
    return respuesta.json().get("results", [])