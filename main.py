from pyexpat import model
from dotenv import load_dotenv
from fastapi import FastAPI, Form, Request
from google import genai
from pydantic import BaseModel
import os
from google.genai import types
from typing import Annotated
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import chromadb
from chromadb.utils import embedding_functions
from pypdf import PdfReader

chroma_client = chromadb.PersistentClient(path="./university_db")
sentence_transformer_ef = embedding_functions.DefaultEmbeddingFunction()
collection = chroma_client.get_collection(
    name="university_info", 
    embedding_function=sentence_transformer_ef
)

load_dotenv()
app = FastAPI() 

templates = Jinja2Templates(directory="templates")


client = genai.Client(api_key=os.getenv("API_KEY"))

my_config = types.GenerateContentConfig(
system_instruction=(
        "You are a concise assistant. "
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

chat_req = []

@app.post("/chat", response_class=HTMLResponse)
def chat_bot(req: Request, user_input: Annotated[str, Form()]):
    # Query the DB for the 3 most relevant text chunks
    results = collection.query(
        query_texts=[user_input],
        n_results=3
    )
    retrieved_context = "\n\n".join(results['documents'][0])
    augmented_message = f"""
        You are a helpful assistant for my university.
        Use the following retrieved context to answer the question below. 
        If the answer isn't in the context, say you don't know.

        CONTEXT FROM DATABASE:
        {retrieved_context}

        USER QUESTION:
        {user_input}
        """

    chat_req.append(user_input)
    
    response = chat.send_message(augmented_message)
    
    chat_req.append(response.text)


    return templates.TemplateResponse("home.html", {"request": req, "chat_responses": chat_req})

@app.get("/home", response_class=HTMLResponse)
def welcome(req: Request):
    return templates.TemplateResponse("home.html", {"request": req})














































@app.get("/health")
def healt_check():
    return {
        "message":"All Good"
    }