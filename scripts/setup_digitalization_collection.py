#!/usr/bin/env python3
"""
Setup Weaviate Collection for Digitalization Reports
=====================================================

Creates the Weaviate schema and optionally uploads digitalization reports.

Usage:
    python scripts/setup_digitalization_collection.py
    python scripts/setup_digitalization_collection.py --upload-docs ./docs/digitalization_report.pdf
"""

import os
import sys
import argparse
from pathlib import Path
import weaviate
from weaviate.auth import AuthApiKey
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()


def create_collection(client):
    """Create the DigitalizationReport collection in Weaviate"""

    collection_name = "DigitalizationReport"

    # Check if collection already exists
    try:
        schema = client.schema.get()
        exists = any(cls['class'] == collection_name for cls in schema.get('classes', []))

        if exists:
            print(f"⚠️  Collection '{collection_name}' already exists.")
            response = input("Delete and recreate? (y/N): ")
            if response.lower() == 'y':
                client.schema.delete_class(collection_name)
                print(f"✅ Deleted existing collection")
            else:
                print("Keeping existing collection")
                return
    except Exception as e:
        print(f"Error checking existing schema: {e}")

    # Define schema
    collection_schema = {
        "class": collection_name,
        "description": "Chunks of digitalization and AI trend reports in the PV industry",
        "vectorizer": "text2vec-openai",  # Use OpenAI embeddings
        "moduleConfig": {
            "text2vec-openai": {
                "model": "text-embedding-3-small",
                "dimensions": 1536,
                "type": "text"
            }
        },
        "properties": [
            {
                "name": "content",
                "dataType": ["text"],
                "description": "The text content of the report chunk",
                "moduleConfig": {
                    "text2vec-openai": {
                        "skip": False,
                        "vectorizePropertyName": False
                    }
                }
            },
            {
                "name": "source",
                "dataType": ["text"],
                "description": "Source document name"
            },
            {
                "name": "page",
                "dataType": ["text"],
                "description": "Page number or section identifier"
            },
            {
                "name": "section",
                "dataType": ["text"],
                "description": "Section or chapter name"
            },
            {
                "name": "date",
                "dataType": ["text"],
                "description": "Publication or update date"
            },
            {
                "name": "metadata",
                "dataType": ["text"],
                "description": "Additional metadata as JSON string"
            }
        ]
    }

    # Create collection
    try:
        client.schema.create_class(collection_schema)
        print(f"✅ Created collection '{collection_name}' successfully!")
        print(f"   - Vectorizer: text2vec-openai (text-embedding-3-small)")
        print(f"   - Properties: content, source, page, section, date, metadata")
    except Exception as e:
        print(f"❌ Failed to create collection: {e}")
        sys.exit(1)


def upload_documents(client, file_paths):
    """
    Upload documents to Weaviate.

    For now, this is a placeholder. You can extend this to:
    1. Parse PDFs
    2. Chunk the text
    3. Upload to Weaviate

    Args:
        client: Weaviate client
        file_paths: List of document paths to upload
    """
    collection_name = "DigitalizationReport"

    print("\n📄 Document Upload")
    print("=" * 60)
    print("⚠️  Document upload requires PDF parsing libraries")
    print("   Install: pip install pypdf2 langchain")
    print("\n💡 For now, you can manually upload documents using:")
    print("   1. Weaviate Console (https://console.weaviate.cloud)")
    print("   2. Custom Python script with PyPDF2 + chunking")
    print("   3. LangChain document loaders")
    print("\n📋 Example upload script:")
    print("""
    from langchain.document_loaders import PyPDFLoader
    from langchain.text_splitter import RecursiveCharacterTextSplitter

    # Load PDF
    loader = PyPDFLoader("digitalization_report.pdf")
    documents = loader.load()

    # Chunk text
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
    chunks = text_splitter.split_documents(documents)

    # Upload to Weaviate
    for chunk in chunks:
        client.data_object.create(
            data_object={
                "content": chunk.page_content,
                "source": chunk.metadata.get("source", ""),
                "page": str(chunk.metadata.get("page", "")),
                "section": "",
                "date": "",
                "metadata": str(chunk.metadata)
            },
            class_name="DigitalizationReport"
        )
    """)


def main():
    parser = argparse.ArgumentParser(description="Setup Digitalization Reports collection in Weaviate")
    parser.add_argument("--upload-docs", nargs="+", help="PDF files to upload")
    parser.add_argument("--skip-create", action="store_true", help="Skip collection creation")
    args = parser.parse_args()

    print("=" * 60)
    print("Weaviate Collection Setup - Digitalization Reports")
    print("=" * 60)

    # Check environment variables
    weaviate_url = os.getenv("WEAVIATE_URL")
    weaviate_api_key = os.getenv("WEAVIATE_API_KEY")
    openai_api_key = os.getenv("OPENAI_API_KEY")

    if not all([weaviate_url, weaviate_api_key, openai_api_key]):
        print("❌ Missing required environment variables:")
        if not weaviate_url:
            print("   - WEAVIATE_URL")
        if not weaviate_api_key:
            print("   - WEAVIATE_API_KEY")
        if not openai_api_key:
            print("   - OPENAI_API_KEY")
        print("\nPlease set these in your .env file")
        sys.exit(1)

    print(f"✅ Weaviate URL: {weaviate_url}")

    # Connect to Weaviate
    try:
        client = weaviate.Client(
            url=weaviate_url,
            auth_client_secret=AuthApiKey(api_key=weaviate_api_key),
            additional_headers={
                "X-OpenAI-Api-Key": openai_api_key
            }
        )
        print("✅ Connected to Weaviate successfully")
    except Exception as e:
        print(f"❌ Failed to connect to Weaviate: {e}")
        sys.exit(1)

    # Create collection
    if not args.skip_create:
        print("\n📦 Creating Collection")
        print("=" * 60)
        create_collection(client)

    # Upload documents
    if args.upload_docs:
        upload_documents(client, args.upload_docs)

    print("\n" + "=" * 60)
    print("✅ Setup complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Upload your digitalization reports to the Weaviate collection")
    print("2. Test the agent: python digitalization_trend_agent.py")
    print("3. Restart your Flask app to use the new agent")


if __name__ == "__main__":
    main()
