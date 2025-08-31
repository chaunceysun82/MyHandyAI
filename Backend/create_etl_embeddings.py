#!/usr/bin/env python3
"""
Script to create embeddings for Test/ETL.py and store them in Qdrant.
This script will:
1. Read the ETL.py file content
2. Chunk the code into manageable pieces
3. Create embeddings using OpenAI
4. Store embeddings in a new Qdrant collection called 'etl_code'
"""

import os
import sys
import uuid
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance
from qdrant_client.http.exceptions import UnexpectedResponse

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def chunk_text(text: str, max_chars: int = 1000) -> List[str]:
    """
    Simple character-based chunker. Produces chunks of <= max_chars.
    For code, we'll also try to break on logical boundaries like function definitions.
    """
    if not text:
        return []
    
    text = text.strip()
    if len(text) <= max_chars:
        return [text]
    
    chunks = []
    lines = text.split('\n')
    current_chunk = ""
    
    for line in lines:
        # If adding this line would exceed max_chars, start a new chunk
        if len(current_chunk) + len(line) + 1 > max_chars and current_chunk:
            chunks.append(current_chunk.strip())
            current_chunk = line
        else:
            if current_chunk:
                current_chunk += '\n' + line
            else:
                current_chunk = line
    
    # Add the last chunk if it exists
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    return chunks

def create_embeddings_for_texts(texts: List[str], model: str = "text-embedding-3-small") -> List[List[float]]:
    """
    Creates embeddings via OpenAI for a list of strings (batched).
    Returns list of embedding vectors in same order as texts.
    """
    if not texts:
        return []
    
    print(f"Creating embeddings for {len(texts)} text chunks using model {model}")
    resp = client.embeddings.create(model=model, input=texts)
    
    return [item.embedding for item in resp.data]

def upsert_embeddings_to_qdrant(
        file_id: str,
        embeddings: List[List[float]],
        texts: List[str],
        extra_payload: Optional[dict] = None,
        collection_name: str = "etl_code"
    ) -> dict:
    """
    Store embeddings in Qdrant with file metadata.
    """
    qdrant_url = os.getenv("QDRANT_URL")
    qdrant_api_key = os.getenv("QDRANT_API_KEY")
    
    if not qdrant_url or not qdrant_api_key:
        raise RuntimeError("QDRANT_URL and QDRANT_API_KEY must be set in environment variables")
    
    print(f"Connecting to Qdrant at {qdrant_url}")
    qclient = QdrantClient(url=qdrant_url, api_key=qdrant_api_key, prefer_grpc=False)
    
    if not embeddings:
        return {"status": "no_embeddings"}
    
    vector_size = len(embeddings[0])
    print(f"Vector size: {vector_size}")
    
    # Create collection if it doesn't exist
    try:
        qclient.get_collection(collection_name=collection_name)
        print(f"Collection '{collection_name}' already exists")
    except UnexpectedResponse as ex:
        if ex.status_code == 404:
            print(f"Creating new collection '{collection_name}'")
            qclient.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )
        else:
            raise
    
    # Create points for Qdrant
    points = []
    for idx, (vec, txt) in enumerate(zip(embeddings, texts)):
        unique_str = f"{file_id}-{idx}"
        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, unique_str))
        
        payload = {
            "file_id": file_id,
            "file_name": "ETL.py",
            "file_path": "Test/ETL.py", 
            "chunk_index": idx,
            "text_preview": txt[:200] + "..." if len(txt) > 200 else txt,
            "full_text": txt,
            "content_type": "python_code"
        }
        
        if extra_payload:
            payload.update(extra_payload)
        
        points.append(PointStruct(id=point_id, vector=vec, payload=payload))
    
    print(f"Upserting {len(points)} points to collection '{collection_name}'")
    qclient.upsert(collection_name=collection_name, points=points)
    
    return {"status": "ok", "num_points": len(points), "collection": collection_name}

def process_etl_file():
    """
    Main function to process the ETL.py file and create embeddings.
    """
    # Path to the ETL.py file
    etl_file_path = os.path.join("..", "Test", "ETL.py")
    
    if not os.path.exists(etl_file_path):
        print(f"❌ ETL.py file not found at {etl_file_path}")
        return
    
    print(f"📄 Reading ETL.py file from {etl_file_path}")
    
    # Read the file content
    try:
        with open(etl_file_path, 'r', encoding='utf-8') as file:
            file_content = file.read()
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return
    
    print(f"📄 File content length: {len(file_content)} characters")
    
    # Chunk the content
    print("✂️ Chunking the file content...")
    chunks = chunk_text(file_content, max_chars=800)  # Slightly smaller chunks for code
    print(f"📄 Created {len(chunks)} chunks")
    
    # Create embeddings
    try:
        print("🔮 Creating embeddings...")
        embeddings = create_embeddings_for_texts(chunks)
        print(f"✅ Created {len(embeddings)} embeddings")
    except Exception as e:
        print(f"❌ Error creating embeddings: {e}")
        return
    
    # Store in Qdrant
    try:
        print("💾 Storing embeddings in Qdrant...")
        file_id = "etl_py_" + str(uuid.uuid4())[:8]  # Generate unique file ID
        
        extra_payload = {
            "description": "ETL script for downloading files from Google Drive and processing them into MongoDB",
            "language": "python",
            "created_by": "embedding_script",
            "file_size": len(file_content)
        }
        
        result = upsert_embeddings_to_qdrant(
            file_id=file_id,
            embeddings=embeddings,
            texts=chunks,
            extra_payload=extra_payload,
            collection_name="etl_code"
        )
        
        print(f"✅ Successfully stored embeddings: {result}")
        return result
        
    except Exception as e:
        print(f"❌ Error storing embeddings: {e}")
        return

if __name__ == "__main__":
    print("🚀 Starting ETL.py embedding creation process...")
    
    # Check required environment variables
    required_vars = ["OPENAI_API_KEY", "QDRANT_URL", "QDRANT_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("Please set these variables in your .env file or environment")
        sys.exit(1)
    
    result = process_etl_file()
    
    if result and result.get("status") == "ok":
        print("🎉 Successfully created and stored embeddings for ETL.py!")
        print(f"📊 Collection: {result.get('collection')}")
        print(f"📈 Number of points: {result.get('num_points')}")
    else:
        print("❌ Failed to create embeddings")
        sys.exit(1)
