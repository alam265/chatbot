from dotenv import load_dotenv
from fastapi import FastAPI
from google import genai
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os

load_dotenv()
app = FastAPI() 


client = genai.Client(api_key=os.getenv("API_KEY"))

@app.get("/health")
def healt_check():
    return {
        "message":"All Good"
    }


@app.get("/chat")
def reply():
    response = client.models.generate_content(
        model = "gemini-3-flash-preview",
        contents="Hey whats up"
    )
    return response.text 



