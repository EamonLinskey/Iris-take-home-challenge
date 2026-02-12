"""
Vector store service - ChromaDB wrapper for semantic search
"""
from typing import List, Dict, Optional
import chromadb
from chromadb.config import Settings
import os
from django.conf import settings as django_settings


class VectorStore:
    """Manage vector storage and retrieval using ChromaDB"""

    def __init__(self, collection_name: str = "document_chunks"):
        """
        Initialize ChromaDB vector store

        Args:
            collection_name: Name of the collection to use
        """
        self.collection_name = collection_name

        # Get persist directory from Django settings
        persist_dir = getattr(
            django_settings,
            'CHROMADB_PERSIST_DIR',
            './chromadb_data'
        )

        # Ensure directory exists
        os.makedirs(persist_dir, exist_ok=True)

        # Initialize ChromaDB client with persistence
        self.client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"description": "Document chunks for RAG retrieval"}
        )

        print(f"ChromaDB initialized. Collection: {collection_name}, Items: {self.collection.count()}")

    def add_chunks(
        self,
        chunk_ids: List[str],
        embeddings: List[List[float]],
        documents: List[str],
        metadatas: List[Dict] = None
    ) -> bool:
        """
        Add document chunks to vector store

        Args:
            chunk_ids: Unique IDs for each chunk
            embeddings: Vector embeddings for each chunk
            documents: Text content of each chunk
            metadatas: Optional metadata for each chunk

        Returns:
            True if successful
        """
        try:
            self.collection.add(
                ids=chunk_ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas or [{} for _ in chunk_ids]
            )
            return True
        except Exception as e:
            print(f"Error adding chunks to vector store: {str(e)}")
            return False

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        where: Dict = None,
        similarity_threshold: float = 0.0
    ) -> Dict:
        """
        Search for similar chunks using vector similarity

        Args:
            query_embedding: Query vector
            top_k: Number of results to return
            where: Optional metadata filter
            similarity_threshold: Minimum similarity score (0-1)

        Returns:
            Dictionary with ids, documents, distances, and metadatas
        """
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where
            )

            # Filter by similarity threshold if specified
            # ChromaDB returns distances (lower = more similar)
            # Convert to similarity scores: similarity = 1 - (distance / 2)
            if similarity_threshold > 0:
                filtered_results = {
                    'ids': [[]],
                    'documents': [[]],
                    'distances': [[]],
                    'metadatas': [[]]
                }

                for idx, distance in enumerate(results['distances'][0]):
                    similarity = 1 - (distance / 2)
                    if similarity >= similarity_threshold:
                        filtered_results['ids'][0].append(results['ids'][0][idx])
                        filtered_results['documents'][0].append(results['documents'][0][idx])
                        filtered_results['distances'][0].append(distance)
                        filtered_results['metadatas'][0].append(results['metadatas'][0][idx])

                return filtered_results

            return results
        except Exception as e:
            print(f"Error searching vector store: {str(e)}")
            return {'ids': [[]], 'documents': [[]], 'distances': [[]], 'metadatas': [[]]}

    def delete_by_document(self, document_id: str) -> bool:
        """
        Delete all chunks belonging to a specific document

        Args:
            document_id: UUID of the document

        Returns:
            True if successful
        """
        try:
            # Delete chunks where metadata contains this document_id
            self.collection.delete(
                where={"document_id": document_id}
            )
            return True
        except Exception as e:
            print(f"Error deleting document chunks: {str(e)}")
            return False

    def get_chunk_by_id(self, chunk_id: str) -> Optional[Dict]:
        """
        Retrieve a specific chunk by ID

        Args:
            chunk_id: Unique chunk ID

        Returns:
            Chunk data or None if not found
        """
        try:
            result = self.collection.get(
                ids=[chunk_id],
                include=["documents", "metadatas", "embeddings"]
            )

            if result['ids']:
                return {
                    'id': result['ids'][0],
                    'document': result['documents'][0],
                    'metadata': result['metadatas'][0],
                    'embedding': result['embeddings'][0]
                }
            return None
        except Exception as e:
            print(f"Error retrieving chunk: {str(e)}")
            return None

    def count(self) -> int:
        """Get total number of chunks in collection"""
        return self.collection.count()

    def reset(self) -> bool:
        """Delete all data from collection (use with caution!)"""
        try:
            self.client.delete_collection(self.collection_name)
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "Document chunks for RAG retrieval"}
            )
            return True
        except Exception as e:
            print(f"Error resetting collection: {str(e)}")
            return False


# Singleton instance for reuse
_vector_store = None

def get_vector_store() -> VectorStore:
    """Get singleton instance of vector store"""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
