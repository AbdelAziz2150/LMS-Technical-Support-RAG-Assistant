# 🎓 LMS Technical Support RAG System

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Flask](https://img.shields.io/badge/Flask-Web%20Framework-black)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--5.2-green)
![ChromaDB](https://img.shields.io/badge/Vector%20DB-ChromaDB-purple)
![License](https://img.shields.io/badge/License-MIT-yellow)

An enterprise-ready **Retrieval-Augmented Generation (RAG)** system
built with Flask that processes LMS technical manuals (.DOCX), indexes
text and image descriptions, and delivers AI-powered technical support
responses.

------------------------------------------------------------------------

## 📑 Table of Contents

-   [Overview](#-overview)
-   [Architecture](#-architecture)
-   [Features](#-features)
-   [Tech Stack](#-tech-stack)
-   [Installation](#-installation)
-   [Usage](#-usage)
-   [API Endpoints](#-api-endpoints)
-   [Project Structure](#-project-structure)
-   [Configuration](#-configuration)
-   [Performance Notes](#-performance-notes)
-   [Future Improvements](#-future-improvements)
-   [Contributing](#-contributing)
-   [License](#-license)

------------------------------------------------------------------------

## 📌 Overview

This system enables AI-powered LMS technical support by:

1.  Uploading LMS manuals in `.DOCX` format
2.  Extracting and chunking textual content
3.  Processing UI screenshots/images using vision models
4.  Storing embeddings in ChromaDB
5.  Generating structured, step-by-step troubleshooting responses

The result is a contextual AI assistant specialized in your LMS
documentation.

------------------------------------------------------------------------

## 🏗 Architecture

                    ┌────────────────────┐
                    │   User Interface   │
                    │     (UI.html)      │
                    └─────────┬──────────┘
                              │
                              ▼
                    ┌────────────────────┐
                    │     Flask API      │
                    │  (/upload, /ask)   │
                    └─────────┬──────────┘
                              │
            ┌─────────────────┼─────────────────┐
            ▼                                   ▼
    ┌─────────────────┐              ┌─────────────────┐
    │ Text Extraction │              │ Image Queue     │
    │ (python-docx)   │              │ Background Job  │
    └─────────┬───────┘              └─────────┬───────┘
              ▼                                  ▼
    ┌──────────────────────────┐     ┌──────────────────────────┐
    │ OpenAI Embeddings        │     │ OpenAI Vision (GPT-5.2)  │
    │ text-embedding-3-large   │     │ UI Element Description   │
    └─────────┬────────────────┘     └─────────┬────────────────┘
              ▼                                  ▼
                    ┌────────────────────────────┐
                    │        ChromaDB            │
                    │ Persistent Vector Store    │
                    └────────────┬───────────────┘
                                 ▼
                    ┌────────────────────────────┐
                    │ OpenAI GPT-5.2             │
                    │ Structured Response Engine │
                    └────────────────────────────┘

------------------------------------------------------------------------

## 🚀 Features

### 📄 Document Processing

-   Secure `.DOCX` uploads (max 16MB)
-   Automatic text chunking (≤ 2000 characters)
-   Image extraction and background processing
-   Secure filename handling

### 🧠 Vector Search

-   OpenAI Embeddings (`text-embedding-3-large`)
-   Persistent ChromaDB storage
-   Hybrid retrieval (text + UI descriptions)

### 👁 Vision Intelligence

-   GPT-5.2 Vision model for UI analysis
-   Detailed UI element descriptions:
    -   Shapes
    -   Colors
    -   Positions
    -   Labels
    -   Functional purpose

### 💬 Structured AI Responses

-   Step-by-step walkthroughs
-   Numbered steps & sub-steps
-   **Bolded UI elements**
-   Conversational yet professional tone

### 🔄 Background Processing

-   Daemon thread for image analysis
-   Queue monitoring endpoint
-   Non-blocking uploads

------------------------------------------------------------------------

## 🛠 Tech Stack

  Layer                Technology
  -------------------- -------------------------------
  Backend              Flask
  Vector Database      ChromaDB
  Embeddings           OpenAI text-embedding-3-large
  LLM                  OpenAI GPT-5.2
  Vision               GPT-5.2 Vision
  Document Parsing     python-docx
  Image Processing     Pillow
  Environment Config   python-dotenv

------------------------------------------------------------------------

## ⚙ Installation

### 1️⃣ Clone Repository

    git clone https://github.com/yourusername/lms-rag-system.git
    cd lms-rag-system

### 2️⃣ Install Dependencies

    pip install -r requirements.txt

If needed, create `requirements.txt`:

    flask
    flask-cors
    python-dotenv
    chromadb
    pillow
    python-docx
    openai

### 3️⃣ Environment Setup

Create `.env`:

    OPENAI_API_KEY=your_openai_api_key_here

------------------------------------------------------------------------

## ▶ Usage

Run the application:

    python app.py

Access at:

    http://localhost:5000

------------------------------------------------------------------------

## 🔌 API Endpoints

### `POST /upload`

Upload and process a `.DOCX` manual.

### `POST /ask`

``` json
{
  "question": "How do I create a course?"
}
```

Streams structured AI responses.

### `GET /documents`

Lists indexed documents.

### `GET /queue-status`

Returns: - Pending images - Processed images - Current image being
analyzed

------------------------------------------------------------------------

## 📂 Project Structure

    lms-rag-system/
    │
    ├── app.py
    ├── chroma_db/
    ├── uploaded_docs/
    ├── image_queue/
    ├── templates/
    │   └── UI.html
    ├── .env
    └── requirements.txt

------------------------------------------------------------------------

## 🔐 Configuration

-   Max upload size: **16MB**
-   Supported file type: **.DOCX only**
-   Vector DB persists in `./chroma_db`
-   CORS enabled for frontend-backend communication

------------------------------------------------------------------------

## 📈 Performance Notes

-   Image-heavy documents may take longer to fully process.
-   Embedding cost scales with document size.
-   Persistent ChromaDB enables fast subsequent queries.
-   Background queue prevents upload bottlenecks.

------------------------------------------------------------------------

## 🔮 Future Improvements

-   PDF support
-   Hybrid keyword + vector search
-   Role-based access control
-   Docker deployment
-   CI/CD integration
-   Streaming token-level UI updates
-   Caching layer (Redis)

------------------------------------------------------------------------

## 🤝 Contributing

Pull requests are welcome.\
For major changes, please open an issue first to discuss improvements.

------------------------------------------------------------------------

## 📜 License

MIT License --- feel free to use and modify.
