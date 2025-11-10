"""Modal service for Qwen2.5-VL-3B relevance scoring."""
import modal

app = modal.App("qwen-relevance-scorer")

CACHE_DIR = "/hf-cache"

model_image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("git")
    .pip_install(
        [
            "transformers>=4.45.0",
            "torch>=2.0.0",
            "torchvision>=0.15.0",
            "qwen-vl-utils==0.0.8",
            "Pillow>=10.0.0",
            "requests>=2.31.0",
            "pydantic>=2.0.0",
            "accelerate>=0.20.0",
            "bitsandbytes>=0.41.0",
            "hf_transfer==0.1.8",
            "fastapi>=0.104.0",
            "uvicorn[standard]>=0.24.0",
        ]
    )
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1", "HF_HUB_CACHE": CACHE_DIR})
)

with model_image.imports():
    import io
    import json
    from typing import Dict, List

    import requests
    import torch
    from PIL import Image
    from qwen_vl_utils import process_vision_info
    from transformers import (
        AutoModelForVision2Seq,
        AutoProcessor,
        BitsAndBytesConfig,
    )


cache_volume = modal.Volume.from_name("hf-hub-cache", create_if_missing=True)


@app.function(
    image=model_image, volumes={CACHE_DIR: cache_volume}, timeout=20 * 60
)
def download_model():
    """Download and cache the Qwen2.5-VL-3B model."""
    from huggingface_hub import snapshot_download
    
    MODEL_NAME = "Qwen/Qwen2.5-VL-3B-Instruct"
    result = snapshot_download(
        MODEL_NAME,
        ignore_patterns=["*.pt", "*.bin"],  # using safetensors
    )
    print(f"Downloaded model weights to {result}")


# Global model components - initialized once per container
model = None
processor = None
device = None

def initialize_model():
    """Initialize model components once per container."""
    global model, processor, device
    
    if model is not None:
        return  # Already initialized
    
    MODEL_NAME = "Qwen/Qwen2.5-VL-3B-Instruct"
    
    # Load processor
    processor = AutoProcessor.from_pretrained(
        MODEL_NAME,
        trust_remote_code=True
    )
    
    # Important for decoder-only models to avoid generation issues
    if hasattr(processor, "tokenizer") and hasattr(processor.tokenizer, "padding_side"):
        try:
            processor.tokenizer.padding_side = "left"
            print("Set tokenizer.padding_side='left' for decoder-only generation")
        except Exception as e:
            print(f"Unable to set tokenizer padding_side: {e}")
    
    # Load model with 8-bit quantization
    bnb_config = BitsAndBytesConfig(
        load_in_8bit=True,
        bnb_8bit_compute_dtype=torch.float16
    )
    
    model = AutoModelForVision2Seq.from_pretrained(
        MODEL_NAME,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True
    )
    
    model.eval()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    # Performance optimizations
    try:
        torch.backends.cuda.matmul.allow_tf32 = True  # perf win on Ampere+
    except Exception:
        pass
    
    print(f"✓ Loaded Qwen2.5-VL-3B model: {MODEL_NAME}")


def _load_image(image_url: str) -> "Image.Image":
    """
    Load an image from URL or local path.
    
    Args:
        image_url: URL string or local file path
        
    Returns:
        PIL Image object
    """
    if image_url.startswith(('http://', 'https://')):
        # Load from URL
        response = requests.get(image_url, timeout=30)
        response.raise_for_status()
        image = Image.open(io.BytesIO(response.content))
    else:
        # Load from local path
        image = Image.open(image_url)
    
    # Convert to RGB if necessary
    if image.mode != 'RGB':
        image = image.convert('RGB')
    
    return image


def _build_relevance_prompt(query: str, page_context: str = "") -> str:
    """
    Build the relevance scoring prompt.
    
    Args:
        query: The user query
        page_context: Optional context about the page
        
    Returns:
        Formatted prompt string
    """
    context_text = f"\nPage Context: {page_context}" if page_context else ""
    
    prompt = f"""You are an expert at analyzing document relevance.

Query: {query}{context_text}

Please analyze the image and determine how relevant it is to answering the query.
Rate the relevance on a scale from 1 to 5:
- 1: Completely irrelevant
- 2: Slightly relevant but not useful
- 3: Moderately relevant, might be useful
- 4: Very relevant and useful
- 5: Highly relevant and essential

Provide your response in the following JSON format:

{{
    "score": 4,
    "reasoning": "Brief explanation of why you gave this score"
}}

Respond ONLY with the JSON object, no additional text."""
    
    return prompt


def _parse_response(output_text: str, page_id: str) -> dict:
    """
    Parse model output into a result dictionary.
    
    Args:
        output_text: Raw text output from the model
        page_id: The page ID being scored
        
    Returns:
        Dictionary with page_id, score, and reasoning
    """
    text = output_text.strip()
    
    # Try to parse JSON from response
    try:
        # Handle case where response might have markdown code blocks
        if "```json" in text:
            json_str = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            json_str = text.split("```")[1].split("```")[0].strip()
        else:
            json_str = text.strip()
        
        data = json.loads(json_str)
        
        score = data.get("score", 3)
        # Ensure score is within valid range
        score = max(1, min(5, int(score)))
        
        return {
            "page_id": page_id,
            "score": score,
            "reasoning": data.get("reasoning", "")
        }
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        # Fallback: return default score
        return {
            "page_id": page_id,
            "score": 3,
            "reasoning": f"Failed to parse structured response: {str(e)}"
        }


def score_relevance(
        query: str,
        page_image_url: str,
        page_id: str,
        page_context: str = "",
        temperature: float = 0.1,
        max_new_tokens: int = 256,
    ) -> Dict:
    """
    Score the relevance of a single page to a query.
    
    Args:
        query: The user query
        page_image_url: URL or local path to page image
        page_id: Identifier for the page
        page_context: Optional context about the page
        temperature: Sampling temperature (lower = more deterministic)
        max_new_tokens: Maximum new tokens to generate
        
    Returns:
        Dictionary with page_id, score (1-5), and reasoning
    """
    # Load image
    page_image = _load_image(page_image_url)
    
    # Build prompt
    prompt_text = _build_relevance_prompt(query, page_context)
    
    # Prepare messages in Qwen VL format
    message_content = [
        {"type": "image", "image": page_image},
        {"type": "text", "text": prompt_text},
    ]
    
    messages = [
        {
            "role": "user",
            "content": message_content,
        }
    ]
    
    # Preparation for inference
    text = processor.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    image_inputs, video_inputs = process_vision_info(messages)
    
    inputs = processor(
        text=[text],
        images=image_inputs,
        videos=video_inputs,
        padding=True,
        return_tensors="pt",
    )
    inputs = inputs.to(device)
    
    # Inference: Generation of the output
    with torch.no_grad():
        # Use bf16 if available for better performance
        use_bf16 = torch.cuda.is_available() and torch.cuda.is_bf16_supported()
        
        if use_bf16:
            with torch.autocast(device_type="cuda", dtype=torch.bfloat16):
                generated_ids = model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                    temperature=temperature,
                    use_cache=True,
                )
        else:
            generated_ids = model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                use_cache=True,
            )
    
    generated_ids_trimmed = [
        out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
    ]
    output_text = processor.batch_decode(
        generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
    )
    
    # Parse and return result
    return _parse_response(output_text[0], page_id)


def batch_score_relevance(
        relevance_inputs: List[Dict],
        temperature: float = 0.1,
        max_new_tokens: int = 256,
        batch_size: int = 4,
    ) -> List[Dict]:
    """
    Score the relevance of multiple pages in batch.
    
    Args:
        relevance_inputs: List of input dictionaries, each containing:
            - query: The user query
            - page_image_url: URL or path to page image
            - page_id: Page identifier
            - page_context: Optional page context
        temperature: Sampling temperature
        max_new_tokens: Maximum new tokens to generate
        batch_size: Number of items to process in each mini-batch
        
    Returns:
        List of result dictionaries with page_id, score, and reasoning
    """
    if not relevance_inputs:
        return []
    
    all_results = []
    use_bf16 = torch.cuda.is_available() and torch.cuda.is_bf16_supported()
    
    # Process in mini-batches to control memory
    for start in range(0, len(relevance_inputs), batch_size):
        end = min(start + batch_size, len(relevance_inputs))
        batch_inputs = relevance_inputs[start:end]
        
        # Load images and prepare messages for batch inference
        messages_batch = []
        page_ids = []
        
        for inp in batch_inputs:
            page_image = _load_image(inp["page_image_url"])
            prompt_text = _build_relevance_prompt(
                inp["query"], 
                inp.get("page_context", "")
            )
            
            message_content = [
                {"type": "image", "image": page_image},
                {"type": "text", "text": prompt_text},
            ]
            
            messages = [{"role": "user", "content": message_content}]
            messages_batch.append(messages)
            page_ids.append(inp["page_id"])
        
        # Prepare batch inputs
        texts = [
            processor.apply_chat_template(m, tokenize=False, add_generation_prompt=True)
            for m in messages_batch
        ]
        
        image_inputs, video_inputs = process_vision_info(messages_batch)
        
        model_inputs = processor(
            text=texts,
            images=image_inputs,
            videos=video_inputs,
            padding=True,
            return_tensors="pt",
        )
        model_inputs = model_inputs.to(device)
        
        # Generate outputs
        with torch.no_grad():
            if use_bf16:
                with torch.autocast(device_type="cuda", dtype=torch.bfloat16):
                    generated_ids = model.generate(
                        **model_inputs,
                        max_new_tokens=max_new_tokens,
                        temperature=temperature,
                        use_cache=True,
                    )
            else:
                generated_ids = model.generate(
                    **model_inputs,
                    max_new_tokens=max_new_tokens,
                    temperature=temperature,
                    use_cache=True,
                )
        
        # Decode outputs
        generated_ids_trimmed = [
            out_ids[len(in_ids):] for in_ids, out_ids in zip(model_inputs.input_ids, generated_ids)
        ]
        output_texts = processor.batch_decode(
            generated_ids_trimmed,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False,
        )
        
        # Parse results
        for output_text, page_id in zip(output_texts, page_ids):
            all_results.append(_parse_response(output_text, page_id))
        
        # Free memory between mini-batches
        try:
            del model_inputs, generated_ids, generated_ids_trimmed, output_texts
        except Exception:
            pass
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    
    return all_results


@app.function(gpu="A10G", image=model_image, volumes={CACHE_DIR: cache_volume}, timeout=20 * 60)
@modal.asgi_app()
def fastapi_app():
    """Create and return FastAPI application with relevance scoring endpoints."""
    # Import inside method to avoid serialization issues
    from typing import Dict, List

    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
    from pydantic import Field as PydanticField
    
    # Initialize model on startup
    initialize_model()
    
    # FastAPI Request/Response Models
    class RelevanceRequest(BaseModel):
        """Request model for single relevance scoring."""
        query: str = PydanticField(..., description="The user query")
        page_image_url: str = PydanticField(..., description="URL or local path to page image")
        page_id: str = PydanticField(..., description="Page identifier")
        page_context: str = PydanticField(default="", description="Optional page context")
        temperature: float = PydanticField(default=0.1, ge=0.0, le=2.0, description="Sampling temperature")
        max_new_tokens: int = PydanticField(default=256, ge=1, le=1024, description="Maximum new tokens to generate")

    class BatchRelevanceRequest(BaseModel):
        """Request model for batch relevance scoring."""
        relevance_inputs: List[Dict] = PydanticField(
            ...,
            description="List of input dictionaries with query, page_image_url, page_id, and optional page_context"
        )
        temperature: float = PydanticField(default=0.1, ge=0.0, le=2.0, description="Sampling temperature")
        max_new_tokens: int = PydanticField(default=256, ge=1, le=1024, description="Maximum new tokens to generate")
        batch_size: int = PydanticField(default=4, ge=1, le=16, description="Mini-batch size for processing")

    class RelevanceResponse(BaseModel):
        """Response model for relevance scoring results."""
        page_id: str = PydanticField(..., description="Page identifier")
        score: int = PydanticField(..., ge=1, le=5, description="Relevance score from 1 to 5")
        reasoning: str = PydanticField(..., description="Explanation of the score")

    class BatchRelevanceResponse(BaseModel):
        """Response model for batch relevance scoring results."""
        results: List[RelevanceResponse] = PydanticField(..., description="List of relevance scoring results")
    
    # Create FastAPI app
    web_app = FastAPI(
        title="Qwen Relevance Scorer API",
        description="REST API for scoring document relevance using Qwen2.5-VL-3B",
        version="1.0.0",
    )
    
    @web_app.get("/")
    async def root():
        """Root endpoint with API information."""
        return {
            "message": "Qwen Relevance Scorer API",
            "model": "Qwen2.5-VL-3B-Instruct",
            "version": "1.0.0",
            "docs": "/docs",
            "endpoints": {
                "score_relevance": "/score_relevance",
                "batch_score_relevance": "/batch_score_relevance",
                "health": "/health"
            }
        }
    
    @web_app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "service": "qwen-relevance-scorer",
            "model": "Qwen2.5-VL-3B-Instruct",
            "model_loaded": model is not None and processor is not None
        }
    
    @web_app.post("/score_relevance", response_model=RelevanceResponse)
    async def score_relevance_endpoint(request: RelevanceRequest):
        """
        Score the relevance of a single page to a query.
        
        Example request:
        ```json
        {
            "query": "What is the total revenue?",
            "page_image_url": "https://example.com/page.jpg",
            "page_id": "page_1",
            "page_context": "Financial report Q1 2024",
            "temperature": 0.1,
            "max_new_tokens": 256
        }
        ```
        """
        try:
            result = score_relevance(
                query=request.query,
                page_image_url=request.page_image_url,
                page_id=request.page_id,
                page_context=request.page_context,
                temperature=request.temperature,
                max_new_tokens=request.max_new_tokens,
            )
            return RelevanceResponse(**result)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Relevance scoring failed: {str(e)}")
    
    @web_app.post("/batch_score_relevance", response_model=BatchRelevanceResponse)
    async def batch_score_relevance_endpoint(request: BatchRelevanceRequest):
        """
        Score the relevance of multiple pages in a single batch request.
        
        Example request:
        ```json
        {
            "relevance_inputs": [
                {
                    "query": "What is the total revenue?",
                    "page_image_url": "https://example.com/page1.jpg",
                    "page_id": "page_1",
                    "page_context": "Financial report Q1 2024"
                },
                {
                    "query": "What is the total revenue?",
                    "page_image_url": "https://example.com/page2.jpg",
                    "page_id": "page_2",
                    "page_context": "Financial report Q1 2024"
                }
            ],
            "temperature": 0.1,
            "max_new_tokens": 256,
            "batch_size": 4
        }
        ```
        """
        try:
            results = batch_score_relevance(
                relevance_inputs=request.relevance_inputs,
                temperature=request.temperature,
                max_new_tokens=request.max_new_tokens,
                batch_size=request.batch_size,
            )
            return BatchRelevanceResponse(
                results=[RelevanceResponse(**result) for result in results]
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Batch relevance scoring failed: {str(e)}")
    
    return web_app


# example curl

# curl -X 'POST' \
#   'https://fluidzero--qwen-relevance-scorer-fastapi-app-dev.modal.run/score_relevance' \
#   -H 'accept: application/json' \
#   -H 'Content-Type: application/json' \
#   -d '{
#   "query": "do lions swim",
#   "page_image_url": "https://unstract.com/wp-content/uploads/2024/12/unstract-API-extract-data-from-pdf-scans-images-ocr-badly-scanned-document-960x1024.png",
#   "page_id": "string",
#   "page_context": "",
#   "temperature": 0.1,
#   "max_new_tokens": 256
# }'
