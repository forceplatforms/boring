import modal

app = modal.App("colpali-indexing")


CACHE_DIR = "/hf-cache"

model_image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("git")
    .pip_install(
        [
            "colpali-engine==0.3.5",
            "transformers>=4.45.0",
            "torch>=2.0.0",
            "hf_transfer==0.1.8",
            "qwen-vl-utils==0.0.8",
            "torchvision==0.19.1",
            "fastapi>=0.104.0",
            "uvicorn[standard]>=0.24.0",
        ]
    )
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1", "HF_HUB_CACHE": CACHE_DIR})
)

with model_image.imports():
    import base64
    import io

    import torch
    from colpali_engine.models import ColPali, ColPaliProcessor
    from PIL import Image


cache_volume = modal.Volume.from_name("hf-hub-cache", create_if_missing=True)

# Global model components - initialized once per container
model = None
processor = None


def initialize_model():
    """Initialize model components once per container."""
    global model, processor

    if model is not None:
        return  # Already initialized

    MODEL_NAME = "vidore/colpali-v1.2"

    model = ColPali.from_pretrained(
        MODEL_NAME,
        torch_dtype=torch.bfloat16,
        device_map="cuda:0",
    ).eval()

    processor = ColPaliProcessor.from_pretrained(MODEL_NAME)
    print(f"✓ Loaded ColPali model: {MODEL_NAME}")


@app.function(image=model_image, volumes={CACHE_DIR: cache_volume}, timeout=20 * 60)
def download_model():
    from huggingface_hub import snapshot_download

    MODEL_NAME = "vidore/colpali-v1.2"
    result = snapshot_download(
        MODEL_NAME,
        ignore_patterns=["*.pt", "*.bin"],  # using safetensors
    )
    print(f"Downloaded model weights to {result}")


@app.function(gpu="L40S", image=model_image, volumes={CACHE_DIR: cache_volume}, timeout=20 * 60)
@modal.asgi_app()
def fastapi_app():
    """Create and return FastAPI application with ColPali embedding endpoints."""
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
    from pydantic import Field as PydanticField

    # Initialize model on startup
    initialize_model()

    def _decode_base64_images(base64_images: list[str]) -> list["Image.Image"]:
        """
        Decode base64 encoded images to PIL Images.

        Args:
            base64_images: List of base64 encoded image strings

        Returns:
            List of PIL Image objects
        """
        images = []
        for b64_str in base64_images:
            try:
                image_bytes = base64.b64decode(b64_str)
                img = Image.open(io.BytesIO(image_bytes))
                # Convert to RGB if necessary
                if img.mode != "RGB":
                    img = img.convert("RGB")
                images.append(img)
            except Exception as e:
                print(f"Error decoding image: {e}")
                # Skip invalid images
                continue
        return images

    def get_embeddings_internal(
        images: list["Image.Image"] | None = None, queries: list[str] | None = None
    ):
        """
        Get embeddings for images or text queries.

        Args:
            images: List of PIL Images (optional)
            queries: List of text query strings (optional)

        Returns:
            Dictionary with 'image_embeddings' and/or 'query_embeddings' keys
        """
        results = {}

        with torch.no_grad():
            if images is not None and len(images) > 0:
                # Process images
                batch_images = processor.process_images(images).to(model.device)
                image_embeddings = model(**batch_images)
                # Convert to list of lists for JSON serialization
                results["image_embeddings"] = image_embeddings.cpu().tolist()

            if queries is not None and len(queries) > 0:
                # Process queries
                batch_queries = processor.process_queries(queries).to(model.device)
                query_embeddings = model(**batch_queries)
                # Convert to list of lists for JSON serialization
                results["query_embeddings"] = query_embeddings.cpu().tolist()

        return results

    # FastAPI Request/Response Models
    class EmbeddingRequest(BaseModel):
        """Request model for getting embeddings."""

        images: list[str] | None = PydanticField(
            default=None, description="List of base64 encoded images"
        )
        queries: list[str] | None = PydanticField(
            default=None, description="List of text queries"
        )

    class EmbeddingResponse(BaseModel):
        """Response model for embeddings."""

        image_embeddings: list[list[list[float]]] | None = PydanticField(
            default=None, description="Image embeddings (batch, patches, embedding_dim)"
        )
        query_embeddings: list[list[list[float]]] | None = PydanticField(
            default=None, description="Query embeddings (batch, tokens, embedding_dim)"
        )

    # Create FastAPI app
    web_app = FastAPI(
        title="ColPali Embeddings API",
        description="REST API for ColPali image and text embeddings",
        version="1.0.0",
    )

    @web_app.get("/")
    async def root():
        """Root endpoint with API information."""
        return {
            "message": "ColPali Embeddings API",
            "model": "vidore/colpali-v1.2",
            "version": "1.0.0",
            "docs": "/docs",
            "endpoints": {
                "get_embeddings": "/get_embeddings",
                "health": "/health",
            },
        }

    @web_app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "service": "colpali-embeddings",
            "model": "vidore/colpali-v1.2",
            "model_loaded": model is not None and processor is not None,
        }

    @web_app.post("/get_embeddings", response_model=EmbeddingResponse)
    async def get_embeddings_endpoint(request: EmbeddingRequest):
        """
        Get embeddings for images and/or text queries.

        Example request:
        ```json
        {
            "images": ["base64_encoded_image_string"],
            "queries": ["a photo of a cat", "what is in this image?"]
        }
        ```
        """
        try:
            # Decode base64 images if provided
            pil_images = None
            if request.images:
                pil_images = _decode_base64_images(request.images)
                if not pil_images:
                    raise HTTPException(
                        status_code=400, detail="Failed to decode any valid images"
                    )

            # Get embeddings
            results = get_embeddings_internal(images=pil_images, queries=request.queries)

            return EmbeddingResponse(**results)
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Embedding generation failed: {str(e)}"
            ) from e

    return web_app


# Keep the class-based interface for backward compatibility
@app.cls(
    image=model_image,
    volumes={CACHE_DIR: cache_volume},
    gpu="L40S",
    timeout=20 * 60,
)
class ColPaliEmbedder:
    """ColPali embedding generator for images and text queries (class-based interface)."""

    @modal.enter()
    def load_model(self):
        """Load the ColPali model and processor on initialization."""
        MODEL_NAME = "vidore/colpali-v1.2"

        self.model = ColPali.from_pretrained(
            MODEL_NAME,
            torch_dtype=torch.bfloat16,
            device_map="cuda:0",
        ).eval()

        self.processor = ColPaliProcessor.from_pretrained(MODEL_NAME)
        print(f"Loaded ColPali model: {MODEL_NAME}")

    @modal.method()
    def get_embeddings(
        self,
        images: list | None = None,
        queries: list | None = None,
    ):
        """
        Get embeddings for images or text queries.

        Args:
            images: List of PIL Images or image paths (optional)
            queries: List of text query strings (optional)

        Returns:
            Dictionary with 'image_embeddings' and/or 'query_embeddings' keys
        """
        results = {}

        with torch.no_grad():
            if images is not None:
                # Process images
                batch_images = self.processor.process_images(images).to(self.model.device)
                image_embeddings = self.model(**batch_images)
                results["image_embeddings"] = image_embeddings.cpu()

            if queries is not None:
                # Process queries
                batch_queries = self.processor.process_queries(queries).to(
                    self.model.device
                )
                query_embeddings = self.model(**batch_queries)
                results["query_embeddings"] = query_embeddings.cpu()

        return results
