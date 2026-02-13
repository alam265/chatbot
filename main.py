import asyncio
from dotenv import load_dotenv
from fastapi import FastAPI, Form, Request, WebSocket, WebSocketDisconnect
from google import genai
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

chat_responses = []

@app.get("/home", response_class=HTMLResponse)
def welcome(req: Request):
    return templates.TemplateResponse("home.html", {"request": req, "chat_responses": chat_responses})


@app.websocket("/ws")
async def chat(websocket: WebSocket):
    
    await websocket.accept() 
    chat_session = client.chats.create(
        model='gemini-3-flash-preview', 
        config=my_config
    )
    
    # Local history for this connection only

    try:
        while True:
            user_input = await websocket.receive_text() 
    

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

            chat_responses.append(user_input)
            
            ai_response = ""
            response_stream = chat_session.send_message_stream(augmented_message)
            for chunk in response_stream:
                    if chunk.text:
                        ai_response += chunk.text
                        await websocket.send_text(chunk.text)
                        await asyncio.sleep(0.07)
            
            chat_responses.append(ai_response)
           

    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"Error: {e}")










































@app.get("/health")
def healt_check():
    return {
        "message":"All Good"
    }