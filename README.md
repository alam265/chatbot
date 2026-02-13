Below is a **GitHub-ready, concise, and professional README.md**, optimized for **project submission**. It’s clean, minimal, and follows common open-source standards.

---

# 🎓 Uni-Bot -- BRAC University Chatbot

A **domain-specific chatbot for BRAC University queries**, built using **Gemini API (Free Tier)** and **FastAPI**, leveraging **Retrieval-Augmented Generation (RAG)** to provide context-aware responses.

> ⚠️ This project is a **work in progress** and requires additional data ingestion to achieve full accuracy.

---

## 📖 About the Project

This chatbot answers queries related to **BRAC University** by retrieving relevant information from a custom knowledge base before generating responses using a large language model.

---

## ✨ Features

* Domain-specific chatbot (BRAC University)
* Gemini API (Free Tier) integration
* FastAPI backend
* Retrieval-Augmented Generation (RAG)
* Scalable document ingestion
* RESTful API design

---

## 🛠️ Tech Stack

* **Language:** Python
* **Backend:** FastAPI
* **LLM:** Gemini API (Free Tier)
* **Architecture:** RAG (Retriever + Generator)
* **Vector Database:** Chroma / FAISS (implementation-dependent)
*  **Frontend:** Bootstrap, CSS 

---

## 🧩 System Architecture

1. User sends a query
2. Relevant documents are retrieved from the vector database
3. Retrieved context is passed to Gemini
4. Gemini generates a grounded response
5. Response is returned via API

---

## 🚀 Getting Started

### Prerequisites

* Python 3.9+
* Gemini API key

### Installation

```bash
git clone www.github.com/alam265/Uni-bot
cd <project-directory>
python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows
```

### Environment Variables

Create a `.env` file:

```env
GEMINI_API_KEY=your_api_key_here
```

### Run the Application

```bash
uvicorn main:app --reload
```



## 📂 Data & Knowledge Base

* The chatbot relies on **custom BRAC University documents**
* Current dataset is **limited**
* More documents will significantly improve accuracy

> ⚠️ Re-embedding is required after adding new documents

---

## 🚧 Known Limitations

* Limited response accuracy due to small dataset
* Free-tier API rate limits

---

## 🔮 Future Work

* Expand BRAC University dataset
* Improve retrieval relevance
* Deploy using Docker
* Role-based access control

---


## 📄 License

This project is intended for **academic and educational use only**.

---

