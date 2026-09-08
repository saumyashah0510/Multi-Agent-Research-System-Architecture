# 📘 Granular 5-Domain Architecture & Execution Guide

This document provides a step-by-step, exhaustive breakdown of all **5 Domain Roles**, explaining how the **UI, Backend API Endpoints, Database Schemas, AI/ML Agents, and DevOps** work together.

---

## 🎯 UI & Paper Storage Concept (Addressing the Paper Review Flow)

> **Question:** When the Search Agent pulls 10 papers, do we show the user 10 full PDFs to read? Where are they stored?

### 1. How the UI handles 10 papers:
- **No full PDF dumping:** Showing 10 full 20-page PDFs on screen would overwhelm the user.
- **Interactive Paper Cards:** Instead, the UI displays **10 interactive summary cards**.
  - Each card shows: **Paper Title**, **Authors**, **Published Year**, **Citation Count**, a **Short Abstract**, a **Direct PDF Link** (to open full PDF in a new tab), and a big **Approve ✅ / Reject ❌** toggle button.
- **User Control:** The user reviews the cards, clicks **Approve** on relevant papers (e.g. 6 papers), clicks **Reject** on irrelevant ones (e.g. 4 papers), and clicks **Submit Approved Papers**.

### 2. Where data is stored:
- **Metadata (Title, Abstract, PDF URL, Approval Status):** Stored in PostgreSQL in the `paper_metadata` table.
- **Raw PDF Files:** Downloaded asynchronously to local storage or an AWS S3 bucket (`data/pdfs/<run_id>/<paper_id>.pdf`).
- **Vector Embeddings (Chunks):** Text chunks from **only approved papers** are embedded into 384-dimensional vectors and stored in PostgreSQL using the **pgvector** extension in the `paper_chunks` table.

---

## 🖥️ DOMAIN 1: Frontend UI Developer (The Interface)

### Owned Technologies:
- React / Next.js (or Streamlit)
- Tailwind CSS
- Lucide React Icons
- Markdown & Math Renderer (`react-markdown`, `remark-math`)

---

### Step-by-Step UI Screens & Components to Build:

#### Screen 1: Research Topic Submission Form
- **UI Elements:**
  - Topic Input Box (e.g., *"Transformers in Medical Image Segmentation"*).
  - Search Scope Slider (5 to 20 papers, default 10).
  - Target Citation Style Selector (Dropdown: APA, IEEE, Harvard, BibTeX).
  - **Start Literature Review** submit button.
- **User Action:** Submitting triggers an API call to `POST /api/v1/research/start` and redirects to the Review Dashboard.

#### Screen 2: Paper Review & Approval Dashboard (Human-in-the-Loop)
- **UI Elements:**
  - Header: Shows current search status (e.g. *"Fetched 10 papers for topic..."*).
  - Card Grid: 10 paper cards.
  - Card Actions: Approve / Reject toggle button for each paper.
  - Footer Action: **Proceed with Approved Papers** button.
- **User Action:** Clicking **Proceed** sends approved paper IDs to `POST /api/v1/research/{run_id}/review`.

#### Screen 3: Literature Review Report Viewer
- **UI Elements:**
  - Real-Time Agent Progress Bar (shows agent progress: Summarizing → Synthesizing → Formatting Citations).
  - Tabbed Report Viewer:
    - **Tab 1: Paper Summaries Table** (Columns: Paper Title, Methodology, Dataset Used, Key Findings, Limitations).
    - **Tab 2: Synthesis Matrix** (Agreements vs Contradictions across papers).
    - **Tab 3: Open Research Gaps** (Unexplored domains).
    - **Tab 4: References & Citations** (Formatted APA/IEEE/BibTeX).
  - **Download Buttons**: Download PDF, Download Markdown, Export BibTeX.

#### Screen 4: Interactive RAG Chat Component
- **UI Elements:**
  - Floating or embedded Chat Drawer beneath the report.
  - Chat Message History (User questions vs AI responses).
  - Input box with **Send** button.
  - Source Citations Popup: Clicking inline citations `[Paper A, 2024]` highlights the exact vector text snippet used.

---

## ⚙️ DOMAIN 2: Backend API & REST Endpoints Developer (The Server)

### Owned Technologies:
- FastAPI (Python 3.11)
- Pydantic v2 (Data Validation)
- Uvicorn (ASGI Web Server)

---

### Step-by-Step REST Endpoints to Build:

#### Endpoint 1: Start Research Run
- **Route:** `POST /api/v1/research/start`
- **Request Body:**
  ```json
  {
    "topic": "Transformers in Medical Image Segmentation",
    "paper_limit": 10,
    "citation_style": "APA"
  }
  ```
- **Response:**
  ```json
  {
    "run_id": "run_987654321",
    "status": "searching",
    "message": "Academic search agent launched."
  }
  ```

#### Endpoint 2: Get Run Progress Status
- **Route:** `GET /api/v1/research/{run_id}/status`
- **Response:**
  ```json
  {
    "run_id": "run_987654321",
    "status": "awaiting_human_review",  // Options: searching, awaiting_human_review, summarizing, completed
    "current_step": "human_review"
  }
  ```

#### Endpoint 3: Fetch Retained Papers for Review
- **Route:** `GET /api/v1/research/{run_id}/papers`
- **Response:**
  ```json
  {
    "run_id": "run_987654321",
    "papers": [
      {
        "paper_id": "paper_01",
        "title": "UNet vs Transformer for MRI Segmentation",
        "authors": ["Dr. Smith", "Dr. Lee"],
        "year": 2024,
        "abstract": "We compare UNet architectures against vision transformers...",
        "pdf_url": "https://arxiv.org/pdf/2401.12345.pdf"
      }
    ]
  }
  ```

#### Endpoint 4: Submit Human Paper Approvals
- **Route:** `POST /api/v1/research/{run_id}/review`
- **Request Body:**
  ```json
  {
    "approved_paper_ids": ["paper_01", "paper_03", "paper_05"],
    "rejected_paper_ids": ["paper_02", "paper_04"]
  }
  ```
- **Response:**
  ```json
  {
    "run_id": "run_987654321",
    "status": "summarizing",
    "message": "LangGraph pipeline resumed for 3 approved papers."
  }
  ```

#### Endpoint 5: Fetch Final Literature Report
- **Route:** `GET /api/v1/research/{run_id}/report`
- **Response:**
  Returns complete structured JSON containing summaries, synthesis matrix, research gaps, and formatted references.

#### Endpoint 6: Interactive RAG Chat Query
- **Route:** `POST /api/v1/chat/query`
- **Request Body:**
  ```json
  {
    "run_id": "run_987654321",
    "question": "Which paper used the BraTS dataset?"
  }
  ```
- **Response:**
  ```json
  {
    "answer": "Paper 01 (Smith et al., 2024) evaluated on the BraTS 2023 dataset...",
    "source_citations": [
      {
        "paper_id": "paper_01",
        "title": "UNet vs Transformer for MRI Segmentation",
        "relevant_chunk": "...evaluated performance on 350 BraTS 2023 MRI scans..."
      }
    ]
  }
  ```

---

## 🗄️ DOMAIN 3: Database & Vector Storage Engineer (The Memory)

### Owned Technologies:
- PostgreSQL 16 (Relational Database)
- **pgvector** Extension (Vector Database)
- SQLAlchemy 2.0 (Python ORM)
- Redis 7 (State Cache & Session Checkpointer)

---

### Step-by-Step Database Tables to Build:

#### Table 1: `research_runs` (Session Tracker)
- `id` (VARCHAR / UUID, Primary Key): e.g. `run_987654321`
- `topic` (TEXT): Research topic submitted by user.
- `citation_style` (VARCHAR): `APA`, `IEEE`, `Harvard`, `BibTeX`.
- `status` (VARCHAR): Current status of the run.
- `created_at` (TIMESTAMP).

#### Table 2: `paper_metadata` (Retrieved Papers Tracker)
- `id` (VARCHAR, Primary Key): e.g. `paper_01`
- `run_id` (UUID, Foreign Key -> `research_runs.id`).
- `title` (TEXT).
- `authors` (JSONB / ARRAY): List of author names.
- `published_year` (INT).
- `abstract` (TEXT).
- `pdf_url` (TEXT).
- `approval_status` (VARCHAR): `pending`, `approved`, `rejected`.

#### Table 3: `paper_chunks` (Vector Storage Table with pgvector)
- `id` (UUID, Primary Key).
- `paper_id` (VARCHAR, Foreign Key -> `paper_metadata.id`).
- `chunk_index` (INT): Chunk number within paper.
- `chunk_text` (TEXT): Raw text content of the 500-token chunk.
- **`embedding` (vector(384))**: 384-dimensional vector embedding generated by HuggingFace `sentence-transformers`.
- **HNSW Index:** Configured with cosine distance indexing (`vector_cosine_ops`) for sub-millisecond similarity search.

#### Table 4: `synthesis_reports` (Final Output Cache)
- `id` (UUID, Primary Key).
- `run_id` (UUID, Foreign Key -> `research_runs.id`).
- `summaries_json` (JSONB): Structured summaries of approved papers.
- `synthesis_matrix_json` (JSONB): Agreements, contradictions, open gaps.
- `formatted_references` (TEXT): Final formatted bibliography.

#### Redis Session Checkpointer:
- Caches active LangGraph state checkpoints (`MemorySaver` / Redis checkpointer) so the pipeline can pause at `human_review` and resume hours later without losing data.

---

## 🧠 DOMAIN 4: AI Agents, LangGraph & ML Specialist (The Brain)

### Owned Technologies:
- Python 3.11
- LangGraph & LangChain
- Groq API / Gemini API / Local Ollama (LLM Options)
- `sentence-transformers` (`all-MiniLM-L6-v2`) (Vector Embedding ML Model)
- PyPDF / pypdf (PDF Parsing)

---

### Step-by-Step Agents & ML Components to Build:

#### ML Component 1: Academic Search Query Expansion
- **What it does:** Uses LLM to expand user topic into optimized academic search terms.
- **Example:** User topic *"Transformers in Medical Segmentation"* -> Expanded search query: `"(transformer OR vision transformer) AND (medical image segmentation OR MRI segmentation)"`.

#### Agent 1: Search & Fetch Agent (`app/agents/search_agent.py`)
- **What it does:** Queries arXiv API and Semantic Scholar API using expanded queries. Pulls metadata (title, abstract, PDF link) for top 10 papers and saves to `paper_metadata` table.

#### Agent 2: Ingestion & Vector RAG Agent (`app/agents/ingestion_agent.py`)
- **What it does:**
  1. Downloads PDFs for approved papers asynchronously.
  2. Extracts text using `PyPDF`.
  3. Splits text into 500-character chunks with 50-character overlaps using `RecursiveCharacterTextSplitter`.
  4. Generates 384-dimensional vector embeddings using local Hugging Face `sentence-transformers`.
  5. Inserts chunks into `paper_chunks` table in PostgreSQL.

#### Agent 3: Summarizer Agent (`app/agents/summarizer_agent.py`)
- **What it does:** Uses strict Pydantic structured output parsing to extract 4 key sections per approved paper:
  ```python
  class PaperSummary(BaseModel):
      methodology: str  # e.g., "Swin Transformer with UNet decoder"
      dataset_used: str  # e.g., "BraTS 2023 MRI Dataset"
      key_findings: str  # e.g., "Achieved 92.4% Dice score, outperforming baseline UNet by 4.1%"
      limitations: str  # e.g., "High computational complexity; tested only on brain MRI"
  ```

#### Agent 4: Synthesis & Gap-Analysis Agent (`app/agents/synthesis_agent.py`)
- **What it does:** Cross-analyzes summaries across all approved papers to build:
  - **Agreements Matrix:** Common findings shared across multiple papers.
  - **Contradictions Matrix:** Conflicting results between authors.
  - **Open Research Gaps:** Future research directions highlighted by authors.

#### Agent 5: Citation & Bibliography Agent (`app/agents/citation_agent.py`)
- **What it does:** Converts paper metadata into requested citation format (APA 7th, IEEE, Harvard, BibTeX) and compiles full Markdown/PDF reports.

#### Agent 6: Interactive RAG Chat Agent (`app/agents/rag_chat_agent.py`)
- **What it does:**
  1. Accepts user chat questions (e.g. *"What evaluation metrics were used?"*).
  2. Embeds the question into a 384-dimensional vector.
  3. Performs cosine distance similarity search in `paper_chunks` table using pgvector.
  4. Retrieves top 3 most relevant text chunks.
  5. Passes retrieved chunks to LLM to generate an accurate answer with inline citations.

---

## 🛡️ DOMAIN 5: DevOps, Security & QA Engineer (The Shield)

### Owned Technologies:
- Docker & Docker Compose
- GitHub Actions CI/CD
- Pre-Commit Hooks
- Ruff, Black, Bandit, Pytest

---

### Step-by-Step Infrastructure & Quality Gatekeepers to Build:

#### 1. Docker Compose Stack (`docker-compose.yml`)
- Spins up 3 containerized microservices locally:
  - **`fastapi-backend`**: Python 3.11 web service.
  - **`postgres-vector`**: PostgreSQL 16 image pre-loaded with `pgvector` extension.
  - **`redis-cache`**: Redis 7 image for agent state checkpointing.

#### 2. Local Pre-Commit Gatekeeper (`.pre-commit-config.yaml`)
- Runs automated checks on every developer's machine before allowing `git commit`:
  - White space & file hygiene checks.
  - **Ruff & Black**: Linter and automatic code formatter.
  - **Bandit**: Static security vulnerability scanner.
  - **Pytest**: Automated test suite execution.

#### 3. GitHub Actions CI/CD Pipeline (`.github/workflows/ci.yml`)
- Cloud security gatekeeper running on Pull Requests targeting `main`.
- Enforces branch protection so no team member can push broken or un-tested code.

#### 4. Master Pytest Suite (`backend/tests/`)
- Unit tests for all 6 agents.
- Integration tests for all FastAPI REST endpoints.

---

This complete guide is now saved in **[docs/DETAILED_DOMAIN_ROLE_GUIDE.md](file:///c:/Users/OMEN/OneDrive/Desktop/Multi-Agent%20Research%20&%20Literature%20Review%20Assistant/docs/DETAILED_DOMAIN_ROLE_GUIDE.md)**! Let me know how you would like to proceed.
