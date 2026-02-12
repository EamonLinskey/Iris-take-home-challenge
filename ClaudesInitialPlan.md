RFP Answer Generation System - Implementation Plan
Context
This is a 3-5 hour take-home challenge to build an AI-powered RFP answer generator. The system ingests company knowledge base documents, extracts and indexes them using RAG (Retrieval Augmented Generation), then generates professional answers to RFP questions using Claude.

Key Requirements:

Must demonstrate AI-assisted development (documenting how AI tools help)
Working core features prioritized over stretch goals
Architecture decisions must be well-documented and understood
Clean, professional frontend for document upload and answer review
Tech Stack (per company preference):

Backend: Django REST Framework
Frontend: Next.js with TypeScript
LLM: Anthropic Claude API (claude-3-5-sonnet)
Vector DB: ChromaDB (embedded mode)
Embeddings: sentence-transformers (local, no API costs)
System Architecture

┌──────────────────────────────────────────────────┐
│         Next.js Frontend (Port 3000)             │
│  Upload Docs → Create RFPs → Review Answers      │
└────────────────┬─────────────────────────────────┘
                 │ REST API
┌────────────────▼─────────────────────────────────┐
│       Django REST Framework (Port 8000)          │
│  ┌──────────┐  ┌─────────┐  ┌────────────────┐  │
│  │ Ingest   │  │   RAG   │  │  Answer Gen    │  │
│  │ Service  │  │ Pipeline│  │  (Claude API)  │  │
│  └────┬─────┘  └────┬────┘  └────────┬───────┘  │
│       │             │                 │          │
│  ┌────▼─────────────▼─────────────────▼───────┐  │
│  │  Django ORM + SQLite                       │  │
│  │  (Documents, RFPs, Questions, Answers)     │  │
│  └────────────────────────────────────────────┘  │
└──────────────┬──────────────────┬────────────────┘
               │                  │
     ┌─────────▼──────┐  ┌────────▼─────────┐
     │   ChromaDB     │  │   Claude API     │
     │  (Vectors)     │  │  (Generation)    │
     └────────────────┘  └──────────────────┘
Data Models
Core Django Models:

Document - Uploaded company knowledge base files (PDF/DOCX/TXT)
DocumentChunk - Text chunks with embeddings stored in both Django + ChromaDB
RFP - RFP submissions containing multiple questions
Question - Individual questions from an RFP
Answer - Generated answers linked to questions and source chunks
Key Relationships:

Document → DocumentChunks (1:many)
RFP → Questions (1:many)
Question → Answer (1:1)
Answer → DocumentChunks (many:many for source attribution)
RAG Pipeline Design
Document Processing Flow
Upload - Accept PDF/DOCX/TXT files via API
Extract - Use PyPDF2/python-docx to get plain text
Chunk - Split into 800-token chunks with 200-token overlap (preserves context)
Embed - Generate embeddings using sentence-transformers (all-MiniLM-L6-v2)
Store - Save chunks to Django DB + vectors to ChromaDB
Answer Generation Flow
Retrieve - Embed question, query ChromaDB for top-5 similar chunks (cosine similarity)
Filter - Only use chunks above 0.7 similarity threshold
Generate - Send question + context chunks to Claude with structured prompt
Save - Store answer with source chunk references and metadata
Key Configuration

CHUNKING = {
    "chunk_size": 800,      # tokens (~600 words)
    "overlap": 200,         # preserve context at boundaries
    "separator": "\n\n"     # respect paragraph structure
}

RETRIEVAL = {
    "top_k": 5,                      # retrieve 5 chunks
    "similarity_threshold": 0.7,     # filter weak matches
    "max_context_tokens": 8000       # leave room for response
}

CLAUDE = {
    "model": "claude-3-5-sonnet-20241022",
    "max_tokens": 2000,
    "temperature": 0.3     # low for consistency
}
API Endpoints
Documents:

POST /api/v1/documents/ - Upload document
GET /api/v1/documents/ - List documents
GET /api/v1/documents/{id}/ - Document detail
DELETE /api/v1/documents/{id}/ - Remove document
RFPs:

POST /api/v1/rfps/ - Create RFP with questions array
GET /api/v1/rfps/ - List RFPs
GET /api/v1/rfps/{id}/ - RFP detail with questions and answers
POST /api/v1/rfps/{id}/generate-answers/ - Generate all answers
Answers:

GET /api/v1/questions/{id}/answer/ - Get answer for question
POST /api/v1/questions/{id}/regenerate/ - Regenerate specific answer
Testing:

POST /api/v1/search/ - Test semantic search (useful for debugging RAG)
Project Structure
Backend (Django)

backend/
├── manage.py
├── requirements.txt
├── .env                          # Environment variables
├── config/
│   ├── settings.py               # Django configuration
│   ├── urls.py                   # Root URLs
│   └── celery.py                 # [Stretch] Celery config
├── rfp_system/
│   ├── models.py                 # ⭐ All Django models
│   ├── serializers.py            # DRF serializers
│   ├── views.py                  # ⭐ API viewsets
│   ├── urls.py                   # App URLs
│   ├── admin.py                  # Django admin
│   ├── tasks.py                  # [Stretch] Celery tasks
│   └── services/
│       ├── document_processor.py # PDF/DOCX extraction
│       ├── chunking.py           # Text splitting
│       ├── embedding.py          # Sentence transformers
│       ├── vector_store.py       # ⭐ ChromaDB wrapper
│       └── generation.py         # ⭐ Claude API integration
├── media/                        # Uploaded files
└── chromadb_data/               # ChromaDB persistence
Frontend (Next.js)

frontend/
├── package.json
├── next.config.js
├── .env.local                    # API URL config
├── src/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx              # Home/Dashboard
│   │   ├── documents/
│   │   │   └── page.tsx          # Document upload & list
│   │   └── rfps/
│   │       ├── page.tsx          # RFP list
│   │       ├── new/
│   │       │   └── page.tsx      # Create RFP form
│   │       └── [id]/
│   │           └── page.tsx      # RFP detail & answers
│   ├── components/
│   │   ├── DocumentUpload.tsx
│   │   ├── DocumentList.tsx
│   │   ├── RFPForm.tsx           # Dynamic question inputs
│   │   ├── AnswerDisplay.tsx
│   │   └── SourceChunks.tsx      # Show source documents
│   ├── lib/
│   │   ├── api.ts                # ⭐ API client
│   │   ├── types.ts              # TypeScript interfaces
│   │   └── utils.ts
│   └── hooks/
│       ├── useDocuments.ts
│       └── useRFPs.ts
⭐ = Critical files (implement these first)

Implementation Timeline (3-5 hours)
Phase 1: Backend Foundation (90 min)
Tasks:

Initialize Django project with DRF
Create all models (Document, DocumentChunk, RFP, Question, Answer)
Run migrations, setup admin panel
Install dependencies: pypdf2, python-docx, sentence-transformers, chromadb, anthropic
Implement document processing pipeline:
Extract text from PDF/DOCX
Chunk text (LangChain RecursiveCharacterTextSplitter)
Generate embeddings (sentence-transformers)
Store in ChromaDB + Django DB
Test with sample PDF
Deliverable: Working document upload → processing → chunked and embedded

Phase 2: RAG + APIs (90 min)
Tasks:

Implement retrieval service (semantic search in ChromaDB)
Implement generation service (Claude API integration)
Create DRF serializers for all models
Implement API viewsets and endpoints
Add generate-answers endpoint
Configure CORS for Next.js
Test all endpoints (Postman/curl)
Deliverable: Complete REST API with RAG answer generation working

Phase 3: Frontend (90 min)
Tasks:

Initialize Next.js with TypeScript + Tailwind CSS
Create API client library
Implement pages:
Documents page with upload (drag-drop)
RFP list page
Create RFP form (dynamic question inputs)
RFP detail page with answers
Implement components:
DocumentUpload with progress
AnswerDisplay with source chunks
Loading states and error handling
Style with Tailwind
Deliverable: Complete frontend with all core features

Phase 4: Integration & Polish (60 min)
Tasks:

End-to-end testing:
Upload documents → process
Create RFP with questions
Generate answers
Display with sources
Fix bugs and edge cases
Add proper error handling
Polish UI/UX (loading states, success messages)
Write documentation (README, setup instructions)
Prepare demo flow
Deliverable: Working system ready to demo

Stretch Goals (if time permits)
Async Processing (45 min): Celery + Redis for background jobs
Confidence Scoring (20 min): Parse JSON from Claude with confidence scores
Answer Caching (30 min): Hash questions to avoid re-generation
Testing: pytest for backend, Jest for frontend
Critical Dependencies
Backend (requirements.txt)

Django==5.0.1
djangorestframework==3.14.0
django-cors-headers==4.3.1
python-decouple==3.8
PyPDF2==3.0.1
python-docx==1.1.0
sentence-transformers==2.3.1
chromadb==0.4.22
anthropic==0.18.1
langchain==0.1.6
tiktoken==0.6.0
Frontend (package.json)

next: 14.1.0
react: 18.2.0
typescript: 5.3.3
tailwindcss: 3.4.1
axios: 1.6.5
react-dropzone: 14.2.3
Environment Variables
Backend (.env)

SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=sqlite:///db.sqlite3
ANTHROPIC_API_KEY=sk-ant-your-api-key
CORS_ALLOWED_ORIGINS=http://localhost:3000
CHROMADB_PERSIST_DIR=./chromadb_data
MAX_UPLOAD_SIZE=52428800  # 50 MB
Frontend (.env.local)

NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
Architecture Decisions & Rationale
Why SQLite?
Faster setup - No separate DB server, zero configuration
Good enough for demo - Handles concurrent reads well
Easy to share - Single file database
Migration path - Can switch to PostgreSQL later if needed
Why sentence-transformers for embeddings?
No API costs - Runs locally, unlimited embeddings
Fast - Good performance on CPU
Quality - all-MiniLM-L6-v2 is solid for general text
Small vectors - 384 dimensions (vs 1536 for OpenAI)
Why ChromaDB embedded?
Simple - No separate server like Pinecone
Local - All data stays on your machine
Persistent - SQLite-backed storage
Production-ready - Can switch to client/server mode later
Why LangChain selectively?
Use: Document loaders (PDF/DOCX) and text splitters - saves ~30 min
Skip: Chains and agents - too complex for timeline
Balance: Get convenience without over-engineering
Synchronous vs Async Processing
Start Synchronous:

Faster to implement (save 45+ minutes)
Good for demo with reasonable file sizes (< 5 MB)
Simple request/response model
Add Celery if time permits:

Better UX for large files
Non-blocking uploads
More production-ready feel
Verification Plan
End-to-End Test Flow
Document Upload:

Upload 2-3 sample PDFs (company docs, product info, case studies)
Verify processing status updates
Check chunks are created in Django admin
Confirm vectors in ChromaDB (count should match chunks)
Semantic Search Test:

Use /api/v1/search/ endpoint
Query: "What are the company's core values?"
Verify relevant chunks returned with similarity scores
Ensures RAG pipeline works before full integration
RFP Creation:

Create RFP with 3-5 questions
Example questions:
"What is your company's experience with enterprise software?"
"Describe your security and compliance certifications"
"What is your typical implementation timeline?"
Verify questions saved correctly
Answer Generation:

Click "Generate Answers" for RFP
Verify loading states work
Check answers generated for all questions
Confirm source chunks displayed with each answer
Validate answers make sense given source documents
Regeneration Test:

Click regenerate on one answer
Verify new answer generated
Check that answers may vary slightly (temperature 0.3)
UI/UX Check:

Error handling works (try uploading invalid file)
Loading states show during processing
Success messages appear
Navigation flows smoothly
Responsive on different screen sizes
Key Metrics to Verify
Document upload → processing time: < 30 seconds for 5-page PDF
Answer generation time: < 10 seconds per question
Chunk retrieval: Returns top-5 chunks in < 1 second
UI responsiveness: No blocking operations
Error recovery: Failed uploads don't break system
Success Criteria
Must Have (Core Features)
✅ Document upload with PDF/DOCX support
✅ Automatic chunking and embedding
✅ ChromaDB vector storage
✅ RFP creation with dynamic questions
✅ Claude-powered answer generation
✅ Source chunk attribution
✅ Clean, functional UI for all operations
✅ End-to-end flow working
Nice to Have (Stretch Goals)
⭐ Async processing with Celery
⭐ Confidence scoring on answers
⭐ Answer caching for repeated questions
⭐ Frontend/backend testing
Documentation Required
README with setup instructions
API documentation (endpoints, request/response)
Architecture decisions explained
AI collaboration notes (how Claude Code was used)
What would be improved with more time
Risk Mitigation
Risk: Large PDF processing timeout

Solution: Start with page limit (first 50 pages) or implement async
Risk: ChromaDB persistence issues

Solution: Explicit persist() calls; keep rebuild script from Django DB
Risk: Claude API rate limits

Solution: Exponential backoff; process answers sequentially not in parallel
Risk: CORS issues between frontend/backend

Solution: Configure django-cors-headers; test early
Risk: File upload failures

Solution: Validate file types; add robust error handling; show clear error messages
Next Steps After Approval
Setup Development Environment:

Create virtual environment for Python
Initialize Django project
Initialize Next.js project
Install all dependencies
Start with Backend (Phase 1):

Models first (foundation for everything)
Then services (document processing, RAG)
Then APIs (expose functionality)
Build Frontend (Phase 3):

API client first
Then pages in order of user flow
Polish as we go
Integrate & Test (Phase 4):

End-to-end testing
Bug fixes
Documentation
Estimated Total Time: 3-4 hours core + 1 hour stretch goals/polish = 4-5 hours total