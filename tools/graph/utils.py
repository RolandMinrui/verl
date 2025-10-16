import numpy as np
import requests
from tqdm import tqdm

URL = "https://api.siliconflow.cn/v1/embeddings"

class EmbeddingClient:
    def __init__(self, api_key: str, model: str = "BAAI/bge-m3", batch_size: int = 16):
        self.api_key = api_key
        self.model = model
        self.batch_size = batch_size
        
    def _batch_encode(self, batch_texts: list[str]) -> list[list[float]]:
        """Encode a single batch of texts"""
        payload = {
            "model": self.model,
            "input": batch_texts,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(URL, json=payload, headers=headers).json()
        return [item['embedding'] for item in response['data']]

    def encode(self, texts: list[str]) -> np.ndarray:
        """Encode texts using a single process"""
        all_embeddings = []
        for i in tqdm(range(0, len(texts), self.batch_size), desc="Generating embeddings in a batch."):
            batch_texts = texts[i:i + self.batch_size]
            batch_embeddings = self._batch_encode(batch_texts)
            all_embeddings.extend(batch_embeddings)
        return np.array(all_embeddings)
    
    def similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> np.ndarray:
        """Compute cosine similarity matrix between two sets of embeddings。
        
        Args:
            emb1: Array of shape [a, b] where a is number of vectors and b is embedding dimension
            emb2: Array of shape [c, b] where c is number of vectors and b is embedding dimension
            
        Returns:
            Similarity matrix of shape [a, c] where element [i, j] is the cosine similarity between emb1[i] and emb2[j]
        """
        # Normalize both embedding matrices along the embedding dimension
        emb1_norm = emb1 / np.linalg.norm(emb1, axis=1, keepdims=True)
        emb2_norm = emb2 / np.linalg.norm(emb2, axis=1, keepdims=True)
        
        # Compute cosine similarity matrix
        similarity_matrix = np.dot(emb1_norm, emb2_norm.T)
        
        return similarity_matrix