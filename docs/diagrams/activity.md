# Activity Diagrams

This document contains end-to-end activity diagrams visualizing control flow across the 9-agent research pipeline, human-in-the-loop paper approval, vector RAG indexing, citation verification, authentication, and multi-style citation export.

## 📌 Table of Contents
1. [1. End-to-End 9-Agent Pipeline Overview](#1-end-to-end-9-agent-pipeline-overview)
2. [2. Search Discovery & Abstract Screening Activity](#2-search-discovery--abstract-screening-activity)
3. [3. Human Approval & "Find More" Loop Activity](#3-human-approval--find-more-loop-activity)
4. [4. PDF Extraction & Vector RAG Indexing Activity](#4-pdf-extraction--vector-rag-indexing-activity)
5. [5. Citation Verification & Structured Report Synthesis Activity](#5-citation-verification--structured-report-synthesis-activity)
6. [6. User Authentication & Session Security Activity](#6-user-authentication--session-security-activity)
7. [7. 5-Style Citation Selection & Download Activity](#7-5-style-citation-selection--download-activity)

---

## 1. End-to-End 9-Agent Pipeline Overview

High-level activity flowchart outlining the complete 9-agent execution graph from prompt submission to structured literature review dashboard rendering.

```mermaid
flowchart TD
    classDef startEnd fill:#2563eb,color:#fff,stroke:#1d4ed8,stroke-width:2px;
    classDef agentNode fill:#0284c7,color:#fff,stroke:#0369a1,stroke-width:2px;
    classDef humanNode fill:#d97706,color:#fff,stroke:#b45309,stroke-width:2px;
    classDef decisionNode fill:#4f46e5,color:#fff,stroke:#4338ca,stroke-width:2px;
    classDef dbNode fill:#059669,color:#fff,stroke:#047857,stroke-width:2px;

    Start([User Submits Query on /research]):::startEnd --> InitState["0. Initialize AgentState Memory"]:::dbNode

    subgraph Stage1 ["Stage 1: Search & Screening"]
        InitState --> A1["1. Query Expansion & Domain Classifier"]:::agentNode
        A1 --> A2["2. Smart Domain-Routed Search & Discovery"]:::agentNode
        A2 --> A3["3. Screening & Relevance Filter"]:::agentNode
    end

    A3 --> HumanPause

    subgraph Stage2 ["Stage 2: Human Approval Interrupt"]
        HumanPause["4. Human-in-the-Loop Interrupt Node"]:::humanNode --> UserDecision{"User UI Action?"}:::decisionNode
    end

    UserDecision -->|Clicks 'Find More'| RouteMore["Set user_decision = 'find_more'"]:::dbNode
    RouteMore --> A1

    UserDecision -->|Clicks 'Approve & Continue'| RouteApprove["Set user_decision = 'continue' & approved_papers"]:::dbNode
    RouteApprove --> Redirect["POST /api/v1/reviews/id/approve -> Redirect to /reviews/id"]:::startEnd

    subgraph Stage3 ["Stage 3: RAG, Verification & Synthesis"]
        Redirect --> A5["5. Full-Text PDF Downloader & Extractor"]:::agentNode
        A5 --> A6["6. Vector Chunking & pgvector RAG Embedding"]:::agentNode
        A6 --> A7["7. Methodology Matrix & Gap Analysis"]:::agentNode
        A7 --> A8["8. Anti-Hallucination Citation Verifier"]:::agentNode
        A8 --> A9["9. Synthesis & Structured JSON Report Agent"]:::agentNode
    end

    A9 --> Finish([Render Interactive Review Dashboard on /reviews/id]):::startEnd
```

| Element | Meaning | Code Reference |
| :--- | :--- | :--- |
| `AgentState` | Shared TypedDict memory state | [backend/app/agents/state.py](../../backend/app/agents/state.py#L7) |
| `build_literature_review_graph()` | LangGraph graph builder | [backend/app/agents/orchestrator.py](../../backend/app/agents/orchestrator.py#L4) |
| `POST /api/v1/reviews/{id}/approve` | Approval transition endpoint | [backend/app/api/v1/reviews.py](../../backend/app/api/v1/reviews.py#L53) |

---

## 2. Search Discovery & Abstract Screening Activity

Detailed activity flowchart for Agents 1, 2, and 3 covering sub-query generation, multi-repository API search, deduplication, and LLM relevance filtering.

```mermaid
flowchart TD
    classDef process fill:#0284c7,color:#fff,stroke:#0369a1,stroke-width:2px;
    classDef decision fill:#4f46e5,color:#fff,stroke:#4338ca,stroke-width:2px;
    classDef store fill:#059669,color:#fff,stroke:#047857,stroke-width:2px;

    Start([Agent 1 Activated]) --> Deconstruct["Deconstruct topic into 3-5 sub-queries"]:::process
    Deconstruct --> Classify["Classify domain: CS / Bio / Interdisciplinary"]:::process
    Classify --> RouteDomain{"Query Domain Target?"}:::decision

    RouteDomain -->|CS / AI / Physics| SearchCS["Query ArXiv, OpenAlex & IEEE"]:::process
    RouteDomain -->|Bio / Medicine| SearchBio["Query PubMed, bioRxiv & Europe PMC"]:::process
    RouteDomain -->|Interdisciplinary| SearchGeneral["Query OpenAlex & Crossref"]:::process

    SearchCS --> Deduplicate["Deduplicate papers by DOI, ArXiv ID, or PMID"]:::process
    SearchBio --> Deduplicate
    SearchGeneral --> Deduplicate

    Deduplicate --> SaveDiscovered["Store candidate list in discovered_papers"]:::store
    SaveDiscovered --> LLMScore["Evaluate query vs abstract relevance with Gemini LLM"]:::process

    LLMScore --> ScoreCheck{"Relevance Score >= 0.6?"}:::decision
    ScoreCheck -->|Yes| Retain["Keep paper & attach score + reasoning"]:::process
    ScoreCheck -->|No| Discard["Filter out off-topic paper"]:::process

    Retain --> SortScreened["Sort screened_papers descending by relevance"]:::store
    Discard --> CheckDone{"All candidate papers scored?"}:::decision
    SortScreened --> CheckDone

    CheckDone -->|No| LLMScore
    CheckDone -->|Yes| PauseNode["Emit Checkpoint 3 & Pause Graph"]:::store
```

| Element | Meaning | Code Reference |
| :--- | :--- | :--- |
| `search_academic_papers()` | Multi-source API search wrapper | [backend/app/services/search_service.py](../../backend/app/services/search_service.py#L356) |
| `screening_node.py` | Gemini LLM abstract relevance scorer | [backend/app/agents/nodes/screening_node.py](../../backend/app/agents/nodes/screening_node.py) |
| `screened_papers` | Relevance-filtered paper array | [backend/app/agents/state.py](../../backend/app/agents/state.py#L14) |

---

## 3. Human Approval & "Find More" Loop Activity

Control flow activity diagram for Agent 4 human-in-the-loop interaction on the frontend `/research` page.

```mermaid
flowchart TD
    classDef ui fill:#d97706,color:#fff,stroke:#b45309,stroke-width:2px;
    classDef decision fill:#4f46e5,color:#fff,stroke:#4338ca,stroke-width:2px;
    classDef api fill:#0284c7,color:#fff,stroke:#0369a1,stroke-width:2px;
    classDef store fill:#059669,color:#fff,stroke:#047857,stroke-width:2px;

    Pause[Graph Paused at Checkpoint 4] --> RenderUI["Render Paper Approval Grid on /research"]:::ui
    RenderUI --> UserInspects["User inspects paper cards & toggles selection checkboxes"]:::ui
    UserInspects --> ActionChoice{"User Button Click?"}:::decision

    ActionChoice -->|Find More Papers| SetFindMore["Set user_decision = 'find_more'"]:::store
    SetFindMore --> CallApproveAPI1["POST /api/v1/reviews/id/approve"]:::api
    CallApproveAPI1 --> LoopBack["Resume Graph -> Conditional Loop Back to Agent 1"]:::api

    ActionChoice -->|Approve & Continue| CheckSelected{"Selected papers count > 0?"}:::decision
    CheckSelected -->|No| DisplayError["Show validation alert: Select at least 1 paper"]:::ui
    DisplayError --> UserInspects

    CheckSelected -->|Yes| SetContinue["Set user_decision = 'continue' & approved_paper_ids"]:::store
    SetContinue --> CallApproveAPI2["POST /api/v1/reviews/id/approve"]:::api
    CallApproveAPI2 --> UpdateDB["UPDATE papers SET is_approved = true"]:::store
    UpdateDB --> Redirect["Redirect user browser to /reviews/id"]:::ui
    Redirect --> ResumeAgent5["Resume Graph Execution -> Proceed to Agent 5"]:::api
```

| Element | Meaning | Code Reference |
| :--- | :--- | :--- |
| `PaperGrid` | Interactive paper selection grid | [frontend/src/components/dashboard/paper-grid.tsx](../../frontend/src/components/dashboard/paper-grid.tsx) |
| `submitHumanDecision()` | Frontend decision API submitter | [frontend/src/lib/api.ts](../../frontend/src/lib/api.ts#L34) |
| `approve_papers()` | Backend approval route handler | [backend/app/api/v1/reviews.py](../../backend/app/api/v1/reviews.py#L53) |

---

## 4. PDF Extraction & Vector RAG Indexing Activity

Activity diagram covering Agent 5 (PDF download & section regex extraction), Agent 6 (500-token chunking & 384D embedding generation into `pgvector`), and Agent 7 (Gap Analysis).

```mermaid
flowchart TD
    classDef process fill:#0284c7,color:#fff,stroke:#0369a1,stroke-width:2px;
    classDef decision fill:#4f46e5,color:#fff,stroke:#4338ca,stroke-width:2px;
    classDef db fill:#059669,color:#fff,stroke:#047857,stroke-width:2px;

    Start([Agent 5 Started]) --> FetchApproved["Fetch list of approved papers"]:::db
    FetchApproved --> DownloadPDF["Download open-access PDF binary via httpx"]:::process
    DownloadPDF --> ParseText["Extract text pages via PyPDF"]:::process
    ParseText --> ExtractSections["Regex match section headers: Intro, Methods, Results, Discussion"]:::process
    ExtractSections --> SaveSections["Store section dictionary in DB paper.sections"]:::db

    SaveSections --> Agent6(["Agent 6: Vector RAG Indexer"]):::process
    Agent6 --> ChunkText["Segment paper text into 500-token passages (50 overlap)"]:::process
    ChunkText --> GenEmbeddings["Generate 384D embeddings via sentence-transformers (all-MiniLM-L6-v2)"]:::process
    GenEmbeddings --> InsertVector["INSERT PaperChunk records with Vector(384) into PostgreSQL pgvector"]:::db

    InsertVector --> Agent7(["Agent 7: Gap Analysis Agent"]):::process
    Agent7 --> VectorSearch["Execute pgvector cosine distance search for experimental paradigms"]:::process
    VectorSearch --> MapMatrix["Construct Methodology Comparison Matrix"]:::process
    MapMatrix --> ExtractGaps["Isolate unresolved research gaps and limitations"]:::process
    ExtractGaps --> SaveGaps["Update state: methodology_matrix & research_gaps"]:::db
```

| Element | Meaning | Code Reference |
| :--- | :--- | :--- |
| `download_and_extract_pdf()` | Async PDF downloader & section parser | [backend/app/services/pdf_service.py](../../backend/app/services/pdf_service.py#L185) |
| `store_paper_chunks()` | Passage chunker & 384D embedding generator | [backend/app/services/vector_service.py](../../backend/app/services/vector_service.py#L140) |
| `PaperChunk` | `pgvector` database ORM model | [backend/app/models/chunk.py](../../backend/app/models/chunk.py#L28) |

---

## 5. Citation Verification & Structured Report Synthesis Activity

Activity diagram for Agent 8 anti-hallucination citation cross-referencing and Agent 9 structured Pydantic JSON synthesis.

```mermaid
flowchart TD
    classDef process fill:#0284c7,color:#fff,stroke:#0369a1,stroke-width:2px;
    classDef decision fill:#4f46e5,color:#fff,stroke:#4338ca,stroke-width:2px;
    classDef db fill:#059669,color:#fff,stroke:#047857,stroke-width:2px;

    Start([Agent 8 Activated]) --> CollectRefs["Collect generated DOIs, PMIDs & ArXiv IDs from draft"]:::process
    CollectRefs --> VerifyExternal["Cross-check identifiers against OpenAlex & Crossref APIs"]:::process
    VerifyExternal --> RefValid{"Citation valid & ground-truth confirmed?"}:::decision

    RefValid -->|Yes| AttachKey["Attach canonical URL & formatted reference string"]:::process
    RefValid -->|No| CorrectRef["Flag ungrounded claim or correct reference metadata"]:::process

    AttachKey --> SaveRefs["Update state: verified_references"]:::db
    CorrectRef --> SaveRefs

    SaveRefs --> Agent9(["Agent 9: Synthesis Report Agent"]):::process
    Agent9 --> PreparePrompt["Assemble verified data, RAG passages & Pydantic schema"]:::process
    PreparePrompt --> CallGemini["Execute Gemini LLM with Pydantic JSON Mode"]:::process
    CallGemini --> ValidateJSON{"JSON matches required Pydantic schema?"}:::decision

    ValidateJSON -->|No| RetryLLM["Retry Gemini call with structured correction prompt"]:::process
    RetryLLM --> CallGemini

    ValidateJSON -->|Yes| SaveReview["UPDATE literature_reviews SET synthesized_review = JSON, status = 'completed'"]:::db
    SaveReview --> PublishComplete["Publish final event: review:id:events status='completed'"]:::db
    PublishComplete --> Finish([Render Full Review Dashboard on /reviews/id]):::process
```

| Element | Meaning | Code Reference |
| :--- | :--- | :--- |
| `synthesis_node.py` | Pydantic JSON literature review synthesizer | [backend/app/agents/nodes/synthesis_node.py](../../backend/app/agents/nodes/synthesis_node.py) |
| `literature_reviews` | Review storage database table | [backend/app/models/review.py](../../backend/app/models/review.py) |
| `redis_service.py` | Real-time event publisher | [backend/app/services/redis_service.py](../../backend/app/services/redis_service.py) |

---

## 6. User Authentication & Session Security Activity

Control flow activity diagram detailing user registration, password hashing, login token generation, and protected API route authorization.

```mermaid
flowchart TD
    classDef ui fill:#d97706,color:#fff,stroke:#b45309,stroke-width:2px;
    classDef process fill:#0284c7,color:#fff,stroke:#0369a1,stroke-width:2px;
    classDef decision fill:#4f46e5,color:#fff,stroke:#4338ca,stroke-width:2px;
    classDef db fill:#059669,color:#fff,stroke:#047857,stroke-width:2px;

    Start([User Visits App]) --> AuthCheck{"JWT token present in localStorage?"}:::decision

    AuthCheck -->|No| GuestMode["Allow guest prompt entry or prompt login"]:::ui
    AuthCheck -->|Yes| ValidToken{"Token signature valid & unexpired?"}:::decision

    ValidToken -->|No| ClearSession["Clear invalid token & redirect to /auth/login"]:::ui
    ValidToken -->|Yes| ActiveUser["Attach Authorization: Bearer token to API requests"]:::process

    GuestMode --> UserSignup["User submits signup form on /auth/signup"]:::ui
    UserSignup --> HashPassword["Hash password using bcrypt"]:::process
    HashPassword --> InsertUser["INSERT into users table"]:::db
    InsertUser --> IssueToken["Generate JWT bearer token & return to client"]:::process
    IssueToken --> StoreLocal["Save JWT token in browser localStorage"]:::ui

    ActiveUser --> AccessRoute["Access protected route GET /api/v1/reviews/"]:::api
    AccessRoute --> MiddlewareCheck["Middleware decodes JWT & extracts user_id"]:::process
    MiddlewareCheck --> DBQuery["Execute SQL query scoped to user_id"]:::db
    DBQuery --> RenderDashboard["Render user's personal reviews list"]:::ui
```

| Element | Meaning | Code Reference |
| :--- | :--- | :--- |
| `users` | User authentication database model | [backend/app/models/user.py](../../backend/app/models/user.py) |
| `api.ts` | Frontend JWT storage & header injector | [frontend/src/lib/api.ts](../../frontend/src/lib/api.ts) |
| `Dashboard.tsx` | Authenticated dashboard page view | [frontend/src/pages/Dashboard.tsx](../../frontend/src/pages/Dashboard.tsx) |

---

## 7. 5-Style Citation Selection & Download Activity

Activity diagram illustrating citation format selection (APA, IEEE, MLA, Harvard, Chicago) and client-side `.txt` file export.

```mermaid
flowchart TD
    classDef ui fill:#d97706,color:#fff,stroke:#b45309,stroke-width:2px;
    classDef process fill:#0284c7,color:#fff,stroke:#0369a1,stroke-width:2px;
    classDef decision fill:#4f46e5,color:#fff,stroke:#4338ca,stroke-width:2px;
    classDef db fill:#059669,color:#fff,stroke:#047857,stroke-width:2px;

    Start([User on Review Dashboard]) --> SelectStyle["Select citation style from CustomDropdown chip"]:::ui
    SelectStyle --> Choice{"Selected Format?"}:::decision

    Choice -->|APA| RequestAPA["GET /api/v1/reviews/id/citations?style=APA"]:::process
    Choice -->|IEEE| RequestIEEE["GET /api/v1/reviews/id/citations?style=IEEE"]:::process
    Choice -->|MLA| RequestMLA["GET /api/v1/reviews/id/citations?style=MLA"]:::process
    Choice -->|Harvard| RequestHarvard["GET /api/v1/reviews/id/citations?style=Harvard"]:::process
    Choice -->|Chicago| RequestChicago["GET /api/v1/reviews/id/citations?style=Chicago"]:::process

    RequestAPA --> FetchMetadata["SELECT paper.authors, title, year, doi FROM papers"]:::db
    RequestIEEE --> FetchMetadata
    RequestMLA --> FetchMetadata
    RequestHarvard --> FetchMetadata
    RequestChicago --> FetchMetadata

    FetchMetadata --> FormatString["Backend formats reference strings according to target style"]:::process
    FormatString --> ReturnJSON["Return JSON List of formatted citation strings"]:::process
    ReturnJSON --> RenderList["Display styled citations in References Dashboard Tab"]:::ui

    RenderList --> ClickDownload["User clicks 'Download Citations (.txt)'"]:::ui
    ClickDownload --> CreateBlob["Construct plain text file Blob in browser memory"]:::process
    CreateBlob --> TriggerDownload["Trigger browser file download: citations_review_id.txt"]:::ui
```

| Element | Meaning | Code Reference |
| :--- | :--- | :--- |
| `citationOptions` | 5-style dropdown configuration | [frontend/src/components/ResearchInput.tsx](../../frontend/src/components/ResearchInput.tsx#L109-L115) |
| `CustomDropdown` | Dropdown selector component | [frontend/src/components/ResearchInput.tsx](../../frontend/src/components/ResearchInput.tsx#L9) |
| `GET /api/v1/reviews/{id}/citations` | Citation formatting API route | [backend/app/api/v1/reviews.py](../../backend/app/api/v1/reviews.py) |
