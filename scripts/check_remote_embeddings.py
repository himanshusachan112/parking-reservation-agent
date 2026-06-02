"""
Check remote Hugging Face Hub embeddings availability.

Usage:
  pip install -r requirements.txt
  Set .env: EMBEDDING_PROVIDER=hf_hub, HUGGINGFACEHUB_API_TOKEN, EMBEDDING_MODEL
  python scripts/check_remote_embeddings.py

The script instantiates the HF Hub embeddings client and encodes sample texts.
"""
import os
import sys
from dotenv import load_dotenv

# Ensure project root is on sys.path so `config` imports work when run as a script.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Load .env from project root
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from config.settings import settings


def main():
    provider = getattr(settings, "embedding_provider", "local")
    if provider != "hf_hub":
        print(f"EMBEDDING_PROVIDER is set to '{provider}'. Set EMBEDDING_PROVIDER=hf_hub to test remote embeddings.")
        sys.exit(2)

    token = settings.huggingfacehub_api_token or None
    model_id = settings.embedding_model
    if "/" not in model_id:
        print("EMBEDDING_MODEL must be a full Hugging Face repo ID when using hf_hub.")
        print("Example: sentence-transformers/all-MiniLM-L6-v2")
        print(f"Current EMBEDDING_MODEL: {model_id}")
        sys.exit(2)

    try:
        from huggingface_hub import InferenceClient
    except Exception as e:
        print("Failed to import huggingface_hub. Install the required package:")
        print("  pip install huggingface-hub python-dotenv")
        print("Import error:", e)
        sys.exit(1)

    print("Initializing Hugging Face Inference client...")
    try:
        client = InferenceClient(token=token) if token else InferenceClient()
    except Exception as e:
        print("Failed to initialize InferenceClient:", e)
        sys.exit(1)

    samples = [
        "Hello world",
        "How many EV charging spots are available today?",
        "What are the parking hours on Sunday?",
    ]

    try:
        vectors = client.feature_extraction(samples, model=settings.embedding_model)
        print(f"Successfully extracted features for {len(samples)} samples.")
        print(f"  Response type: {type(vectors)}")
        try:
            print(f"  First sample length: {len(vectors[0])}")
            print(f"  First values: {vectors[0][:5]}")
        except Exception:
            print("  Response does not support indexing/display as expected.")
    except Exception as e:
        print("Embedding call failed:", e)
        print("If you are using a private or gated model, make sure your Hugging Face token has inference access.")
        print("For public models, you can leave HUGGINGFACEHUB_API_TOKEN blank and use a public model repo ID.")
        sys.exit(1)


if __name__ == "__main__":
    main()
