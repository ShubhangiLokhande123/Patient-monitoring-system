"""
Concierge Triage Agent - FastAPI Application Entry Point

AI-powered post-discharge patient monitoring system.
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from config import settings
from database import init_db, seed_sample_data
from services.rag_service import rag_service

# Import routers
from routers import chat_router, patients_router, alerts_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler - startup and shutdown events."""
    # Startup
    print("Starting Concierge Triage Agent...")
    
    # Initialize database
    init_db()
    print("Database initialized")
    
    # Seed sample data
    seed_sample_data()
    print("Sample data loaded")
    
    # Index clinical guidelines (optional, may take a moment)
    try:
        count = rag_service.index_clinical_guidelines()
        print(f"Indexed {count} clinical documents for RAG")
    except Exception as e:
        print(f"Warning: Could not index clinical guidelines: {e}")
    
    print(f"Server ready at http://{settings.HOST}:{settings.PORT}")
    
    yield
    
    # Shutdown
    print("Shutting down Concierge Triage Agent...")


# Create FastAPI app
app = FastAPI(
    title="Concierge Triage Agent",
    description="""
AI-powered post-discharge patient monitoring system.

## Features

- **Multi-Agent Architecture**: Supervisor agent coordinates specialized agents for PHI protection, vitals intake, and clinical triage
- **Real-time Risk Scoring**: LACE-index based risk scores with vitals modifiers
- **Red Flag Detection**: Pattern-based and LLM-enhanced detection of emergency/urgent symptoms
- **RAG-Grounded Responses**: Answers to patient questions grounded in clinical guidelines
- **PHI Protection**: Microsoft Presidio for HIPAA-compliant data handling

## Agents

1. **PHI Deidentifier** - Sanitizes input/output for HIPAA compliance
2. **Vitals Intake** - Structured daily check-in through natural conversation
3. **Clinical Triage** - Detects red flags and calculates risk scores
4. **Supervisor** - Orchestrates all agents and manages conversation flow

## API Endpoints

- `/chat` - Patient conversation endpoints
- `/patients` - Patient management
- `/alerts` - Alerts and dashboard statistics
    """,
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat_router, prefix="/api")
app.include_router(patients_router, prefix="/api")
app.include_router(alerts_router, prefix="/api")


@app.get("/")
async def root():
    """Root endpoint - serve dashboard."""
    return FileResponse(os.path.join(os.path.dirname(__file__), "static", "index.html"))


@app.get("/api")
async def api_info():
    """API information endpoint."""
    return {
        "name": "Concierge Triage Agent",
        "version": "0.1.0",
        "description": "AI-powered post-discharge patient monitoring system",
        "docs": "/docs",
        "openapi": "/openapi.json",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "llm_configured": bool(settings.GOOGLE_API_KEY),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
