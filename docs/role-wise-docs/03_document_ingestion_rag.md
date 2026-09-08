# Role Workbook: Member 3 - Document Ingestion & Vector RAG Pipeline

## 📋 Role Overview & Scope
- **Role:** PDF Processing & Vector Database Engineer.
- **Goal:** Download paper PDFs, clean raw text, perform semantic chunking, generate embeddings, and index vector chunks into PostgreSQL (pgvector).
- **Owned Files:**
  - `backend/app/services/pdf_service.py`
  - `backend/app/services/vector_store.py`
  - `backend/app/agents/ingestion_agent.py`
  - `backend/tests/test_pdf_service.py`
  - `backend/tests/test_vector_store.py`

---

## 🎯 Step-by-Step Task Breakdown
1. PDF Downloading & AWS S3 caching (or local temp storage).
2. Text Cleaning & Semantic Chunking (using PyPDF/Unstructured + RecursiveCharacterTextSplitter).
3. Embedding Generation & pgvector similarity search indexing.
4. Unit tests in `backend/tests/test_pdf_service.py` and `backend/tests/test_vector_store.py`.
