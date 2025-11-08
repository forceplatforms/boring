"""
ComplianceGuard AI - FastAPI Application Entry Point
SEC Cybersecurity Compliance Gap Detection System
"""

from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from complianceguard import __version__
from complianceguard.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    print(f"🚀 ComplianceGuard AI v{__version__} starting up...")
    print(f"📝 Environment: {settings.environment}")
    print(f"🔗 API Docs: http://localhost:8000/docs")
    yield
    # Shutdown
    print("👋 ComplianceGuard AI shutting down...")


# Create FastAPI application
app = FastAPI(
    title="ComplianceGuard AI",
    description="""
    ## SEC Cybersecurity Compliance Gap Detection System

    Automatically detect SEC cybersecurity disclosure violations by comparing
    internal incident reports against public SEC filings using AI-powered analysis.

    ### Features

    * 📄 **Document Management**: Upload and manage CISO reports and SEC filings
    * 🔍 **Compliance Scanning**: Trigger AI-powered compliance analysis
    * ⚠️ **Violation Detection**: Identify material omissions and misstatements
    * 📊 **Analytics**: Track violations, trends, and remediation status

    ### Compliance Frameworks

    * SEC Regulation S-K Item 1C (Cybersecurity Disclosure)
    * SOX (Sarbanes-Oxley Act)
    * GDPR, CCPA, HIPAA (Coming soon)

    ### API Flow

    1. Upload CISO report (PDF/DOCX)
    2. Upload SEC filing (PDF/DOCX)
    3. Trigger compliance scan
    4. Review detected violations
    5. Assign and remediate violations
    """,
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    contact={
        "name": "ComplianceGuard Team",
        "email": "team@complianceguard.ai",
        "url": "https://complianceguard.ai",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    swagger_ui_parameters={
        "defaultModelsExpandDepth": 2,
        "defaultModelExpandDepth": 2,
        "displayRequestDuration": True,
        "filter": True,
        "showExtensions": True,
        "tryItOutEnabled": True,
    },
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)


# Root endpoint
@app.get(
    "/",
    tags=["Root"],
    summary="API Root",
    description="Get basic API information and links",
)
async def root():
    """API root endpoint with basic information."""
    return {
        "name": "ComplianceGuard AI",
        "version": __version__,
        "status": "operational",
        "timestamp": datetime.utcnow().isoformat(),
        "documentation": {
            "swagger_ui": "/docs",
            "redoc": "/redoc",
            "openapi_json": "/openapi.json",
        },
        "endpoints": {
            "health": "/health",
            "documents": "/api/v1/documents",
            "scans": "/api/v1/scans",
            "violations": "/api/v1/violations",
        },
    }


# Health check endpoint
@app.get(
    "/health",
    tags=["Health"],
    summary="Health Check",
    description="Check overall system health and service availability",
    response_model=dict,
)
async def health_check():
    """
    Comprehensive health check endpoint.

    Returns the overall health status and individual service statuses.
    Used by load balancers and monitoring systems.
    """
    return {
        "status": "healthy",
        "version": __version__,
        "environment": settings.environment,
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "api": {"status": "healthy", "message": "API is operational"},
            "database": {
                "status": "healthy",
                "message": "Database connection available (mock)",
            },
            "redis": {"status": "healthy", "message": "Redis connection available (mock)"},
            "minio": {"status": "healthy", "message": "MinIO storage available (mock)"},
            "landing_ai": {
                "status": "healthy",
                "message": "Landing AI service available (mock)",
            },
            "aws_bedrock": {
                "status": "healthy",
                "message": "AWS Bedrock available (mock)",
            },
        },
    }


# Readiness probe
@app.get(
    "/health/ready",
    tags=["Health"],
    summary="Readiness Probe",
    description="Check if application is ready to accept traffic",
)
async def readiness():
    """Kubernetes readiness probe."""
    return {"status": "ready", "timestamp": datetime.utcnow().isoformat()}


# Liveness probe
@app.get(
    "/health/live",
    tags=["Health"],
    summary="Liveness Probe",
    description="Check if application is alive",
)
async def liveness():
    """Kubernetes liveness probe."""
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}


# Import and register API routers
from complianceguard.api.v1 import documents, scans, violations

app.include_router(
    documents.router,
    prefix=settings.api_v1_prefix,
    tags=["Documents"],
)

app.include_router(
    scans.router,
    prefix=settings.api_v1_prefix,
    tags=["Scans"],
)

app.include_router(
    violations.router,
    prefix=settings.api_v1_prefix,
    tags=["Violations"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Handle unexpected exceptions."""
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "internal_server_error",
            "message": "An unexpected error occurred",
            "details": str(exc) if settings.debug else None,
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "complianceguard.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
