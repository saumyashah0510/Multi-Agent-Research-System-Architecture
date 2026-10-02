# Sequence Diagrams

This document contains end-to-end sequence diagrams detailing user authentication, search initialization, human-in-the-loop paper approval, real-time WebSocket event streaming, modal inspection, review retrieval, and multi-style citation downloads.

## 📌 Table of Contents
1. [1. User Authentication Flow](#1-user-authentication-flow)
2. [2. Research Initialization & Early Screening](#2-research-initialization--early-screening)
3. [3. Human-in-the-Loop Approval & "Find More" Loop](#3-human-in-the-loop-approval--find-more-loop)
4. [4. Review Processing & Real-Time WebSocket Streaming](#4-review-processing--real-time-websocket-streaming)
5. [5. Checkpoint History & PDF Section Modal Data Fetching](#5-checkpoint-history--pdf-section-modal-data-fetching)
6. [6. Past Reviews Listing & Detail Retrieval](#6-past-reviews-listing--detail-retrieval)
7. [7. 5-Style Citation Selection & Download Flow](#7-5-style-citation-selection--download-flow)

---

## 1. User Authentication Flow

Sequence of HTTP calls for user signup, password hashing, JWT token issue, and protected endpoint authorization.

```mermaid
sequenceDiagram
    autonumber
    actor User as Researcher
    participant FE as React Frontend
    participant API as FastAPI Router
    participant DB as PostgreSQL DB

    User->>FE: Fills email & password on /auth/signup
    activate FE
    FE->>API: POST /api/v1/auth/signup {email, password}
    activate API
    API->>DB: Check if user email exists
    activate DB
    DB-->>API: Email available
    deactivate DB
    API->>DB: INSERT into users (email, hashed_password)
    activate DB
    DB-->>API: User record created (id: 42)
    deactivate DB
    API-->>FE: HTTP 201 Created {user_id: 42, token: "JWT-Token"}
    deactivate API
    FE->>FE: Save JWT in localStorage
    FE-->>User: Redirect to /research
    deactivate FE

    User->>FE: Returns later and submits login on /auth/login
    activate FE
    FE->>API: POST /api/v1/auth/login {email, password}
    activate API
    API->>DB: SELECT hashed_password FROM users WHERE email = ?
    activate DB
    DB-->>API: User record found
    deactivate DB
    API->>API: Verify bcrypt password hash
    API-->>FE: HTTP 200 OK {token: "JWT-Token", token_type: "bearer"}
    deactivate API
    FE->>FE: Save JWT in localStorage
    FE-->>User: Authenticated state active
    deactivate FE
```

| Element | Meaning | Code Reference |
| :--- | :--- | :--- |
| `POST /api/v1/auth/signup` | Planned signup route handler | [backend/app/models/user.py](../../backend/app/models/user.py) |
| `POST /api/v1/auth/login` | Planned login route handler | [backend/app/models/user.py](../../backend/app/models/user.py) |
| `users` | User identity ORM model | [backend/app/models/user.py](../../backend/app/models/user.py) |

---

## 2. Research Initialization & Early Screening

Sequence showing initial topic prompt submission, review creation in database, and initial candidate paper screening (Checkpoints 1-3).

```mermaid
sequenceDiagram
    autonumber
    actor User as Researcher
    participant FE as React Frontend
    participant API as FastAPI Router
    participant DB as PostgreSQL DB
    participant Redis as Redis Cache
    participant AG as LangGraph Orchestrator

    User->>FE: Submits topic prompt & citation format on /research
    activate FE
    FE->>API: POST /api/v1/reviews/ {query, max_papers: 10}
    activate API
    API->>DB: INSERT into literature_reviews (user_query, status: "pending")
    activate DB
    DB-->>API: LiteratureReview created (id: 101)
    deactivate DB
    API->>AG: Async launch build_literature_review_graph(review_id: 101)
    API-->>FE: HTTP 202 Accepted {review_id: 101, status: "pending"}
    deactivate API

    AG->>AG: Agent 1: Deconstruct query into 3 sub-queries
    AG->>Redis: Publish review:101:events (Checkpoint 1)
    AG->>Redis: Query cache for academic papers
    alt Cache Miss
        AG->>AG: Agent 2: Search ArXiv, PubMed, OpenAlex
        AG->>Redis: Cache raw search papers (TTL 3600s)
    end
    AG->>Redis: Publish review:101:events (Checkpoint 2)
    AG->>AG: Agent 3: Score abstracts with Gemini LLM (score >= 0.6)
    AG->>DB: INSERT into review_logs (Checkpoint 3 completed)
    AG->>Redis: Publish review:101:events (Checkpoint 3)
    AG->>AG: Pause graph at Checkpoint 4 (Human Interrupt)
    FE-->>User: Render Paper Approval Grid with screened papers
    deactivate FE
```

| Element | Meaning | Code Reference |
| :--- | :--- | :--- |
| `POST /api/v1/reviews/` | Create review task endpoint | [backend/app/api/v1/reviews.py](../../backend/app/api/v1/reviews.py#L33) |
| `build_literature_review_graph()` | Orchestrator state graph compilation | [backend/app/agents/orchestrator.py](../../backend/app/agents/orchestrator.py#L4) |
| `search_academic_papers()` | Multi-source literature fetcher | [backend/app/services/search_service.py](../../backend/app/services/search_service.py#L356) |

---

## 3. Human-in-the-Loop Approval & "Find More" Loop

Sequence showing human paper selection approval or triggering the conditional loop back to discover additional literature.

```mermaid
sequenceDiagram
    autonumber
    actor User as Researcher
    participant FE as React Frontend
    participant API as FastAPI Router
    participant DB as PostgreSQL DB
    participant AG as LangGraph Orchestrator

    User->>FE: Inspects screened papers on /research
    alt User clicks "Find More Papers"
        User->>FE: Clicks "Find More Papers"
        activate FE
        FE->>API: POST /api/v1/reviews/101/approve {user_decision: "find_more", approved_paper_ids: []}
        activate API
        API->>DB: UPDATE review_logs SET user_decision = 'find_more'
        API->>AG: Resume graph (Conditional Loop Back)
        API-->>FE: HTTP 200 OK {status: "searching_more"}
        deactivate API
        AG->>AG: Loop back to Agent 1 (Expand queries & search deeper)
        FE-->>User: Re-renders loading animation with sub-query expansion
        deactivate FE
    else User approves papers
        User->>FE: Selects paper checkboxes & clicks "Approve & Continue"
        activate FE
        FE->>API: POST /api/v1/reviews/101/approve {user_decision: "continue", approved_paper_ids: [1, 2, 5]}
        activate API
        API->>DB: UPDATE papers SET is_approved = true WHERE id IN (1, 2, 5)
        activate DB
        DB-->>API: Records updated
        deactivate DB
        API->>AG: Resume graph execution (Proceed to Agent 5)
        API-->>FE: HTTP 200 OK {status: "approved", approved_count: 3}
        deactivate API
        FE-->>User: Instant redirect to /reviews/101
        deactivate FE
    end
```

| Element | Meaning | Code Reference |
| :--- | :--- | :--- |
| `submitHumanDecision()` | Frontend approval dispatcher | [frontend/src/lib/api.ts](../../frontend/src/lib/api.ts#L34) |
| `POST /api/v1/reviews/{id}/approve` | Backend paper approval route | [backend/app/api/v1/reviews.py](../../backend/app/api/v1/reviews.py#L53) |
| `PaperGrid` | Interactive paper selection grid | [frontend/src/components/dashboard/paper-grid.tsx](../../frontend/src/components/dashboard/paper-grid.tsx) |

---

## 4. Review Processing & Real-Time WebSocket Streaming

Sequence showing real-time event streaming over WebSockets backed by Redis Pub/Sub as Agents 5 through 9 execute.

```mermaid
sequenceDiagram
    autonumber
    actor User as Researcher
    participant FE as React Frontend
    participant WS as FastAPI WebSocket Manager
    participant Redis as Redis PubSub Channel
    participant AG as LangGraph Orchestrator
    participant DB as PostgreSQL DB

    FE->>WS: Connect ws://localhost:8000/api/v1/reviews/101/ws
    activate WS
    WS->>Redis: Subscribe to channel review:101:events
    activate Redis
    WS-->>FE: Connection Established (TCP Stream Active)

    AG->>AG: Agent 5: Download PDFs & parse sections
    AG->>Redis: PUBLISH review:101:events {event: "checkpoint_update", step: 5}
    Redis-->>WS: Push real-time event frame
    WS-->>FE: WS Message frame (Step 5 PDF Extractor Completed)
    FE->>FE: Update Checkpoint Stepper UI Card

    AG->>AG: Agent 6: Chunk text (500 tokens) & generate 384D embeddings
    AG->>DB: INSERT into paper_chunks
    AG->>Redis: PUBLISH review:101:events {event: "checkpoint_update", step: 6}
    Redis-->>WS: Push real-time event frame
    WS-->>FE: WS Message frame (Step 6 pgvector Indexing Completed)

    AG->>AG: Agent 7: Gap analysis & methodology matrix
    AG->>Redis: PUBLISH review:101:events {event: "checkpoint_update", step: 7}
    Redis-->>WS: Push real-time event frame
    WS-->>FE: WS Message frame (Step 7 Gap Analysis Completed)

    AG->>AG: Agent 8: Verify citations against real DOIs
    AG->>Redis: PUBLISH review:101:events {event: "checkpoint_update", step: 8}
    Redis-->>WS: Push real-time event frame
    WS-->>FE: WS Message frame (Step 8 Anti-Hallucination Completed)

    AG->>AG: Agent 9: Synthesize structured Pydantic review JSON
    AG->>DB: UPDATE literature_reviews SET synthesized_review = JSON, status = "completed"
    AG->>Redis: PUBLISH review:101:events {event: "checkpoint_update", step: 9, status: "completed"}
    Redis-->>WS: Push final completion event
    deactivate Redis
    WS-->>FE: WS Message frame (Step 9 Review Synthesized)
    deactivate WS
    FE-->>User: Render Full Literature Review Dashboard on /reviews/101
```

| Element | Meaning | Code Reference |
| :--- | :--- | :--- |
| `ws://.../reviews/{id}/ws` | WebSocket event streaming endpoint | [backend/app/api/v1/reviews.py](../../backend/app/api/v1/reviews.py) |
| `review:{id}:events` | Redis Pub/Sub event channel | [backend/app/services/redis_service.py](../../backend/app/services/redis_service.py) |
| `store_paper_chunks()` | RAG passage embedding generator (384D) | [backend/app/services/vector_service.py](../../backend/app/services/vector_service.py#L140) |

---

## 5. Checkpoint History & PDF Section Modal Data Fetching

Sequence showing user interactions with the mid-step checkpoint log audit drawer and PDF section popup modal.

```mermaid
sequenceDiagram
    autonumber
    actor User as Researcher
    participant FE as React Frontend
    participant API as FastAPI Router
    participant DB as PostgreSQL DB

    User->>FE: Clicks "View Checkpoint History" on /reviews/101
    activate FE
    FE->>API: GET /api/v1/reviews/101/checkpoints
    activate API
    API->>DB: SELECT * FROM review_logs WHERE review_id = 101 ORDER BY step_number ASC
    activate DB
    DB-->>API: List of 9 review log records
    deactivate DB
    API-->>FE: HTTP 200 OK List[{step_number, title, display_summary, payload}]
    deactivate API
    FE-->>User: Open Checkpoint History Drawer Modal with step logs
    deactivate FE

    User->>FE: Clicks "View Extracted Sections" on Step 5 card
    activate FE
    FE->>API: GET /api/v1/reviews/101
    activate API
    API->>DB: SELECT paper.sections FROM papers WHERE review_id = 101 AND is_approved = true
    activate DB
    DB-->>API: Approved paper section dictionary JSON
    deactivate DB
    API-->>FE: HTTP 200 OK {sections: {Methods: "...", Results: "...", Limitations: "..."}}
    deactivate API
    FE-->>User: Open PDF Sections Modal with collapsible section tabs
    deactivate FE
```

| Element | Meaning | Code Reference |
| :--- | :--- | :--- |
| `GET /api/v1/reviews/{id}/checkpoints` | Audit trail endpoint | [backend/app/api/v1/reviews.py](../../backend/app/api/v1/reviews.py) |
| `download_and_extract_pdf()` | PDF section parser | [backend/app/services/pdf_service.py](../../backend/app/services/pdf_service.py#L185) |
| `review_logs` | Checkpoint log table | [backend/app/models/log.py](../../backend/app/models/log.py) |

---

## 6. Past Reviews Listing & Detail Retrieval

Sequence showing retrieval of historical review sessions on `/reviews` and loading detailed reports.

```mermaid
sequenceDiagram
    autonumber
    actor User as Researcher
    participant FE as React Frontend
    participant API as FastAPI Router
    participant DB as PostgreSQL DB

    User->>FE: Navigates to /reviews page
    activate FE
    FE->>API: GET /api/v1/reviews/ (Authorization: Bearer JWT)
    activate API
    API->>DB: SELECT id, user_query, status, created_at FROM literature_reviews WHERE user_id = ?
    activate DB
    DB-->>API: List of literature review summaries
    deactivate DB
    API-->>FE: HTTP 200 OK List[{id: 101, user_query: "AI Radiology", status: "completed"}]
    deactivate API
    FE-->>User: Render Past Reviews Grid on /reviews
    deactivate FE

    User->>FE: Clicks on Review Card #101
    activate FE
    FE->>API: GET /api/v1/reviews/101
    activate API
    API->>DB: SELECT * FROM literature_reviews WHERE id = 101
    activate DB
    DB-->>API: Full literature review record with synthesized_review JSON
    deactivate DB
    API-->>FE: HTTP 200 OK {id: 101, user_query: "...", synthesized_review: {...}}
    deactivate API
    FE-->>User: Render Detailed Review Dashboard on /reviews/101
    deactivate FE
```

| Element | Meaning | Code Reference |
| :--- | :--- | :--- |
| `GET /api/v1/reviews/` | List user reviews endpoint | [backend/app/api/v1/reviews.py](../../backend/app/api/v1/reviews.py#L33) |
| `GET /api/v1/reviews/{id}` | Review detail endpoint | [backend/app/api/v1/reviews.py](../../backend/app/api/v1/reviews.py#L43) |
| `Dashboard.tsx` | Dashboard route view | [frontend/src/pages/Dashboard.tsx](../../frontend/src/pages/Dashboard.tsx) |

---

## 7. 5-Style Citation Selection & Download Flow

Sequence showing citation style selection (APA, IEEE, MLA, Harvard, Chicago) and client-side `.txt` plain text file export.

```mermaid
sequenceDiagram
    autonumber
    actor User as Researcher
    participant FE as React Frontend
    participant API as FastAPI Router
    participant DB as PostgreSQL DB

    User->>FE: Selects "IEEE" from Citation Style dropdown
    activate FE
    FE->>API: GET /api/v1/reviews/101/citations?style=IEEE
    activate API
    API->>DB: SELECT papers.authors, title, published_year, doi, arxiv_id FROM papers WHERE review_id = 101
    activate DB
    DB-->>API: List of verified paper records
    deactivate DB
    API->>API: Format paper metadata into IEEE citation string standard
    API-->>FE: HTTP 200 OK List[{key: "Ref1", formatted_citation: "[1] A. Smith, 'Title', 2023."}]
    deactivate API
    FE-->>User: Display IEEE formatted references in References Tab
    deactivate FE

    User->>FE: Clicks "Download Citations (.txt)" button
    activate FE
    FE->>FE: Construct plain text file blob of formatted citations
    FE-->>User: Trigger browser download (citations_review_101.txt)
    deactivate FE
```

| Element | Meaning | Code Reference |
| :--- | :--- | :--- |
| `citationOptions` | 5-style dropdown configuration | [frontend/src/components/ResearchInput.tsx](../../frontend/src/components/ResearchInput.tsx#L109-L115) |
| `GET /api/v1/reviews/{id}/citations` | Citation formatting API route | [backend/app/api/v1/reviews.py](../../backend/app/api/v1/reviews.py) |
| `CustomDropdown` | Dropdown selector component | [frontend/src/components/ResearchInput.tsx](../../frontend/src/components/ResearchInput.tsx#L9) |
