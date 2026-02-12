from pyexpat import model
from dotenv import load_dotenv
from fastapi import FastAPI, Form
from google import genai
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
from google.genai import types
from typing import Annotated

load_dotenv()
app = FastAPI() 


client = genai.Client(api_key=os.getenv("API_KEY"))

my_config = types.GenerateContentConfig(
system_instruction=(
        "You are a concise assistant. "
        "Always answer the user's question in 2-3 sentences first. "
        "Only add a 'Details' section if the topic is complex or requires deep explanation."
        "Try to answer it in bullet points"
    ),
    temperature=0.7 
)


# Create a chat session
chat = client.chats.create(
    model='gemini-3-flash-preview',
    config=my_config
    )

@app.post("/chat")
def chat_bot(user_input: Annotated[str, Form()]):

    response = chat.send_message(user_input)

    return response.text 

















































@app.get("/health")
def healt_check():
    return {
        "message":"All Good"
    }