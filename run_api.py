#!/usr/bin/env python
"""
Quick start script for ComplianceGuard AI API.
Runs the API server with sensible defaults for local development.
"""

import sys
import uvicorn

if __name__ == "__main__":
    print("=" * 70)
    print("🚀 Starting ComplianceGuard AI API Server")
    print("=" * 70)
    print()
    print("📋 API Documentation:")
    print("   → Swagger UI: http://localhost:8000/docs")
    print("   → ReDoc:      http://localhost:8000/redoc")
    print("   → OpenAPI:    http://localhost:8000/openapi.json")
    print()
    print("🔌 Endpoints:")
    print("   → Documents:  http://localhost:8000/api/v1/documents")
    print("   → Scans:      http://localhost:8000/api/v1/scans")
    print("   → Violations: http://localhost:8000/api/v1/violations")
    print()
    print("💡 Tip: Press Ctrl+C to stop the server")
    print("=" * 70)
    print()

    try:
        uvicorn.run(
            "complianceguard.main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info",
        )
    except KeyboardInterrupt:
        print("\n👋 Shutting down ComplianceGuard AI API Server")
        sys.exit(0)
