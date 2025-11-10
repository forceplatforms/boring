import base64
import json
import os

import requests
from PIL import Image  # Used to create a dummy image for testing

# -----------------------------------------------------------------------------
# Modal FastAPI endpoint URL
# -----------------------------------------------------------------------------

MODAL_URL = "https://fluidzero--colpali-indexing-fastapi-app.modal.run/get_embeddings"


def image_to_base64(image_path: str) -> str | None:
    """Converts an image file to a base64 string."""
    if not os.path.exists(image_path):
        print(f"Error: Image path not found: {image_path}")
        return None

    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode("utf-8")


def get_colpali_embeddings(image_paths: list = None, queries: list = None):
    """
    Calls the Modal endpoint to get embeddings for a list of images
    and/or a list of text queries.
    """
    print("--- Calling ColPali Embedding Endpoint ---")

    payload = {}

    # 1. Process images if provided
    if image_paths:
        print(f"Encoding {len(image_paths)} image(s) to base64...")
        base64_images = []
        for path in image_paths:
            b64_str = image_to_base64(path)
            if b64_str:
                base64_images.append(b64_str)

        if base64_images:
            payload["images"] = base64_images

    # 2. Process text queries if provided
    if queries:
        print(f"Adding {len(queries)} text querie(s)...")
        payload["queries"] = queries

    if not payload:
        print("No valid images or queries provided. Exiting.")
        return

    headers = {"Content-Type": "application/json", "accept": "application/json"}

    print(f"Sending request to {MODAL_URL}...")
    try:
        response = requests.post(MODAL_URL, headers=headers, json=payload, timeout=300)

        # Raise an exception if the request failed (e.g., 4xx, 5xx)
        response.raise_for_status()

        print("Status Code:", response.status_code)
        data = response.json()
        print("Response JSON (keys):", data.keys())

        # 3. Print summary of results (ColPali uses multi-vector embeddings)
        if "image_embeddings" in data:
            num_images = len(data["image_embeddings"])
            print(f"Received {num_images} image embedding(s).")
            if data["image_embeddings"] and len(data["image_embeddings"][0]) > 0:
                num_patches = len(data["image_embeddings"][0])
                embedding_dim = len(data["image_embeddings"][0][0])
                print(f"  Patches per image: {num_patches}")
                print(f"  Embedding dimension: {embedding_dim}")
                print(f"  Total shape: [{num_images}, {num_patches}, {embedding_dim}]")

        if "query_embeddings" in data:
            num_queries = len(data["query_embeddings"])
            print(f"Received {num_queries} query embedding(s).")
            if data["query_embeddings"] and len(data["query_embeddings"][0]) > 0:
                num_tokens = len(data["query_embeddings"][0])
                embedding_dim = len(data["query_embeddings"][0][0])
                print(f"  Tokens per query: {num_tokens}")
                print(f"  Embedding dimension: {embedding_dim}")
                print(f"  Total shape: [{num_queries}, {num_tokens}, {embedding_dim}]")

        # Uncomment the line below to print the full embedding vectors
        # print(json.dumps(data, indent=2))

    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        print(f"Response content: {response.text}")
    except requests.exceptions.RequestException as req_err:
        print(f"An error occurred: {req_err}")
    except json.JSONDecodeError:
        print(f"Failed to decode JSON response: {response.text}")


if __name__ == "__main__":
    # --- Example Usage ---
    # Use the actual image from the resources folder
    from pathlib import Path

    # Try to find the mixture_the_cauldron.png image
    script_dir = Path(__file__).parent
    image_path = script_dir.parent / "resources" / "mixture_the_cauldron.png"

    if image_path.exists():
        print(f"Using image: {image_path}")
        image_files_to_process = [str(image_path)]
    else:
        # Fallback: Create a dummy image file for testing
        DUMMY_IMAGE = "my_test_image.jpg"
        try:
            print(f"Creating dummy image '{DUMMY_IMAGE}' for this example...")
            img = Image.new("RGB", (100, 100), color="red")
            img.save(DUMMY_IMAGE)
            image_files_to_process = [DUMMY_IMAGE]
        except Exception as e:
            print(f"An error occurred during test setup: {e}")
            image_files_to_process = []

    text_queries_to_process = ["a photo of a red square", "a dog playing in a park"]

    # Call the function
    if image_files_to_process:
        get_colpali_embeddings(
            image_paths=image_files_to_process, queries=text_queries_to_process
        )

        # Clean up dummy image if it was created
        if not image_path.exists() and os.path.exists("my_test_image.jpg"):
            os.remove("my_test_image.jpg")
            print("\nCleaned up 'my_test_image.jpg'.")
    else:
        print("No images available for testing.")
