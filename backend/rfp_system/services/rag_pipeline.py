"""
RAG Pipeline - Orchestrates the complete document processing and answer generation flow
"""
from typing import List, Dict, Optional
from django.core.files.uploadedfile import UploadedFile
import uuid
import os

from .document_processor import DocumentProcessor
from .chunking import TextChunker
from .embedding import get_embedding_service
from .vector_store import get_vector_store
from .generation import get_answer_generator


class RAGPipeline:
    """Orchestrate the complete RAG pipeline for document processing and QA"""

    def __init__(self):
        """Initialize pipeline components"""
        self.doc_processor = DocumentProcessor()
        self.chunker = TextChunker(
            chunk_size=800,
            chunk_overlap=200
        )
        self.embedding_service = get_embedding_service()
        self.vector_store = get_vector_store()
        self.answer_generator = get_answer_generator()

    def process_document(
        self,
        document_instance,
        file_path: str
    ) -> Dict:
        """
        Process a document: extract text, chunk, embed, and store

        Args:
            document_instance: Django Document model instance
            file_path: Path to the uploaded file

        Returns:
            Dictionary with processing results
        """
        from ..models import DocumentChunk  # Import here to avoid circular imports

        try:
            # Update status
            document_instance.processing_status = 'processing'
            document_instance.save()

            # Extract text
            text = self.doc_processor.extract_text(
                file_path=file_path,
                file_type=document_instance.file_type
            )

            if not text:
                raise ValueError("Could not extract text from document")

            # Get metadata
            doc_metadata = self.doc_processor.get_metadata(
                file_path=file_path,
                file_type=document_instance.file_type
            )

            # Chunk text
            chunks = self.chunker.chunk_text(
                text=text,
                metadata={
                    'document_id': str(document_instance.id),
                    'filename': document_instance.filename,
                    'file_type': document_instance.file_type,
                    **doc_metadata
                }
            )

            if not chunks:
                raise ValueError("No chunks generated from document")

            # Generate embeddings for all chunks
            chunk_texts = [chunk['content'] for chunk in chunks]
            embeddings = self.embedding_service.embed_batch(chunk_texts)

            # Prepare data for ChromaDB and Django
            chunk_ids = []
            chunk_objects = []

            for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                # Generate unique ID for this chunk
                chunk_id = f"{document_instance.id}_{idx}"
                chunk_ids.append(chunk_id)

                # Create Django DocumentChunk instance
                chunk_obj = DocumentChunk(
                    document=document_instance,
                    chunk_index=idx,
                    content=chunk['content'],
                    chromadb_id=chunk_id,
                    chunk_metadata=chunk['metadata']
                )
                chunk_objects.append(chunk_obj)

            # Bulk create Django chunks
            DocumentChunk.objects.bulk_create(chunk_objects)

            # Add to ChromaDB
            self.vector_store.add_chunks(
                chunk_ids=chunk_ids,
                embeddings=embeddings.tolist(),
                documents=chunk_texts,
                metadatas=[chunk['metadata'] for chunk in chunks]
            )

            # Update document status
            document_instance.processed = True
            document_instance.processing_status = 'completed'
            document_instance.chunk_count = len(chunks)
            document_instance.metadata.update({
                'text_length': len(text),
                'chunk_count': len(chunks),
                **doc_metadata
            })
            document_instance.save()

            return {
                'success': True,
                'chunks_created': len(chunks),
                'text_length': len(text),
                'metadata': doc_metadata
            }

        except Exception as e:
            # Update status to failed
            document_instance.processing_status = 'failed'
            document_instance.metadata['error'] = str(e)
            document_instance.save()

            return {
                'success': False,
                'error': str(e)
            }

    def retrieve_context(
        self,
        question: str,
        top_k: int = 5,
        similarity_threshold: float = 0.3
    ) -> List[Dict]:
        """
        Retrieve relevant context chunks for a question

        Args:
            question: The question to find context for
            top_k: Number of chunks to retrieve
            similarity_threshold: Minimum similarity score

        Returns:
            List of chunk dictionaries with content and metadata
        """
        # Embed the question
        question_embedding = self.embedding_service.embed_text(question)

        # Search vector store
        results = self.vector_store.search(
            query_embedding=question_embedding.tolist(),
            top_k=top_k,
            similarity_threshold=similarity_threshold
        )

        # Format results
        context_chunks = []
        for idx in range(len(results['ids'][0])):
            chunk = {
                'id': results['ids'][0][idx],
                'content': results['documents'][0][idx],
                'similarity': 1 - (results['distances'][0][idx] / 2),  # Convert distance to similarity
                'metadata': results['metadatas'][0][idx]
            }
            context_chunks.append(chunk)

        return context_chunks

    def generate_answer(
        self,
        question: str,
        question_context: str = None,
        include_confidence: bool = False,
        top_k: int = 5,
        use_cache: bool = True
    ) -> Dict:
        """
        Generate an answer to a question using RAG

        Args:
            question: The question to answer
            question_context: Optional additional context
            include_confidence: Whether to include confidence score
            top_k: Number of context chunks to retrieve
            use_cache: Whether to check for cached answers (default: True)

        Returns:
            Dictionary with answer, source chunks, and metadata
        """
        # Check cache first if enabled
        if use_cache:
            from .caching import generate_question_hash, find_cached_answer

            question_hash = generate_question_hash(question)
            cached_answer = find_cached_answer(question_hash)

            if cached_answer:
                # Return cached answer with its source chunks
                source_chunks = []
                for chunk in cached_answer.source_chunks.all():
                    source_chunks.append({
                        'id': chunk.chromadb_id,
                        'content': chunk.content,
                        'similarity': None,  # Cached, no similarity score
                        'metadata': chunk.chunk_metadata
                    })

                return {
                    'answer': cached_answer.answer_text,
                    'confidence_score': cached_answer.confidence_score,
                    'source_chunks': source_chunks,
                    'metadata': {
                        **cached_answer.metadata,
                        'cached': True,
                        'cache_key': question_hash
                    }
                }

        # Retrieve context
        context_chunks = self.retrieve_context(
            question=question,
            top_k=top_k
        )

        if not context_chunks:
            return {
                'answer': "I don't have enough information in the knowledge base to answer this question.",
                'confidence_score': 0.0,
                'source_chunks': [],
                'metadata': {'error': 'No relevant context found'}
            }

        # Extract just the text content for generation
        context_texts = [chunk['content'] for chunk in context_chunks]

        # Generate answer
        result = self.answer_generator.generate_answer(
            question=question,
            context_chunks=context_texts,
            question_context=question_context,
            include_confidence=include_confidence
        )

        # Add source chunks to result
        result['source_chunks'] = context_chunks

        return result

    def delete_document_data(self, document_id: str) -> bool:
        """
        Delete all data associated with a document from vector store

        Args:
            document_id: UUID of the document

        Returns:
            True if successful
        """
        return self.vector_store.delete_by_document(str(document_id))


# Singleton instance
_rag_pipeline = None

def get_rag_pipeline() -> RAGPipeline:
    """Get singleton instance of RAG pipeline"""
    global _rag_pipeline
    if _rag_pipeline is None:
        _rag_pipeline = RAGPipeline()
    return _rag_pipeline
