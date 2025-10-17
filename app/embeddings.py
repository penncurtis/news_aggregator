import json, numpy as np
import hashlib
from typing import List

def embed_text(text: str) -> List[float]:
    # Simple hash-based embedding for now (will replace with sentence-transformers later)
    # This creates a deterministic vector based on text content
    hash_obj = hashlib.md5(text.encode())
    hash_bytes = hash_obj.digest()
    
    # Convert to float vector (normalize to unit length)
    vec = np.array([float(b) for b in hash_bytes[:16]])  # Use first 16 bytes
    vec = vec / (np.linalg.norm(vec) + 1e-9)  # Normalize
    return vec.tolist()

def dumps_embedding(vec: List[float]) -> str:
    return json.dumps(vec)

def loads_embedding(s: str) -> np.ndarray:
    return np.array(json.loads(s), dtype=float)
