"""
Unit tests for service layer (document processing, chunking, embedding, RAG)
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from rfp_system.services.document_processor import DocumentProcessor
from rfp_system.services.chunking import ChunkingService
from rfp_system.services.embedding import EmbeddingService
from rfp_system.services.vector_store import VectorStoreService
from rfp_system.services.generation import GenerationService
from rfp_system.services.rag_pipeline import RAGPipeline


@pytest.mark.unit
class TestDocumentProcessor:
    """Test document processing service"""

    def test_extract_text_from_txt(self, tmp_path):
        """Test extracting text from plain text file"""
        # Create temp text file
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("This is a test document.\nIt has multiple lines.")

        processor = DocumentProcessor()
        text = processor.extract_text(str(txt_file), 'txt')

        assert "This is a test document" in text
        assert "multiple lines" in text

    def test_extract_text_from_pdf(self, sample_pdf_path):
        """Test extracting text from PDF file"""
        processor = DocumentProcessor()
        text = processor.extract_text(sample_pdf_path, 'pdf')

        assert text is not None
        assert len(text) > 0
        assert isinstance(text, str)

    def test_extract_text_unsupported_format(self):
        """Test that unsupported formats raise ValueError"""
        processor = DocumentProcessor()

        with pytest.raises(ValueError, match="Unsupported file type"):
            processor.extract_text("file.xyz", "xyz")

    def test_get_file_metadata_pdf(self, sample_pdf_path):
        """Test extracting metadata from PDF"""
        processor = DocumentProcessor()
        metadata = processor.get_file_metadata(sample_pdf_path, 'pdf')

        assert 'page_count' in metadata
        assert metadata['page_count'] >= 1
        assert 'file_size' in metadata

    def test_process_document_end_to_end(self, sample_pdf_path):
        """Test complete document processing pipeline"""
        processor = DocumentProcessor()
        result = processor.process_document(sample_pdf_path, 'test.pdf', 'pdf')

        assert 'text' in result
        assert 'metadata' in result
        assert len(result['text']) > 0


@pytest.mark.unit
class TestChunkingService:
    """Test text chunking service"""

    def test_chunk_text_basic(self, sample_text):
        """Test basic text chunking"""
        chunker = ChunkingService(chunk_size=800, chunk_overlap=200)
        chunks = chunker.chunk_text(sample_text)

        assert len(chunks) > 0
        assert all(isinstance(chunk, dict) for chunk in chunks)
        assert all('text' in chunk for chunk in chunks)
        assert all('metadata' in chunk for chunk in chunks)

    def test_chunk_indices(self, sample_text):
        """Test that chunks have sequential indices"""
        chunker = ChunkingService()
        chunks = chunker.chunk_text(sample_text)

        for i, chunk in enumerate(chunks):
            assert chunk['metadata']['chunk_index'] == i

    def test_chunk_size_limits(self):
        """Test that chunks respect size limits"""
        text = "word " * 1000  # Create long text
        chunker = ChunkingService(chunk_size=500, chunk_overlap=100)
        chunks = chunker.chunk_text(text)

        for chunk in chunks:
            # Token count should be roughly within chunk_size
            assert chunk['metadata']['token_count'] <= 600  # Some margin

    def test_empty_text(self):
        """Test chunking empty text"""
        chunker = ChunkingService()
        chunks = chunker.chunk_text("")

        assert len(chunks) == 0

    def test_metadata_preservation(self):
        """Test that custom metadata is preserved"""
        chunker = ChunkingService()
        chunks = chunker.chunk_text(
            "Test text",
            metadata={'page': 1, 'source': 'test.pdf'}
        )

        assert chunks[0]['metadata']['page'] == 1
        assert chunks[0]['metadata']['source'] == 'test.pdf'


@pytest.mark.unit
class TestEmbeddingService:
    """Test embedding generation service"""

    def test_singleton_pattern(self):
        """Test that EmbeddingService follows singleton pattern"""
        service1 = EmbeddingService()
        service2 = EmbeddingService()

        assert service1 is service2

    @patch('rfp_system.services.embedding.SentenceTransformer')
    def test_generate_embedding(self, mock_transformer):
        """Test embedding generation"""
        mock_model = Mock()
        mock_model.encode.return_value = [[0.1] * 384]
        mock_transformer.return_value = mock_model

        service = EmbeddingService()
        embedding = service.generate_embedding("Test text")

        assert len(embedding) == 384
        assert all(isinstance(x, float) for x in embedding)
        mock_model.encode.assert_called_once()

    @patch('rfp_system.services.embedding.SentenceTransformer')
    def test_generate_embeddings_batch(self, mock_transformer):
        """Test batch embedding generation"""
        mock_model = Mock()
        mock_model.encode.return_value = [[0.1] * 384, [0.2] * 384, [0.3] * 384]
        mock_transformer.return_value = mock_model

        service = EmbeddingService()
        texts = ["Text 1", "Text 2", "Text 3"]
        embeddings = service.generate_embeddings(texts)

        assert len(embeddings) == 3
        assert all(len(emb) == 384 for emb in embeddings)


@pytest.mark.unit
class TestVectorStoreService:
    """Test vector storage service (ChromaDB wrapper)"""

    @patch('rfp_system.services.vector_store.chromadb.PersistentClient')
    def test_add_chunks(self, mock_client):
        """Test adding chunks to vector store"""
        mock_collection = Mock()
        mock_client.return_value.get_or_create_collection.return_value = mock_collection

        service = VectorStoreService()
        chunks = [
            {
                'id': 'chunk_1',
                'text': 'Sample text',
                'embedding': [0.1] * 384,
                'metadata': {'page': 1}
            }
        ]

        service.add_chunks(chunks)
        mock_collection.add.assert_called_once()

    @patch('rfp_system.services.vector_store.chromadb.PersistentClient')
    def test_search_similar(self, mock_client):
        """Test semantic search in vector store"""
        mock_collection = Mock()
        mock_collection.query.return_value = {
            'ids': [['chunk_1', 'chunk_2']],
            'distances': [[0.2, 0.35]],
            'documents': [['Text 1', 'Text 2']],
            'metadatas': [[{'page': 1}, {'page': 2}]]
        }
        mock_client.return_value.get_or_create_collection.return_value = mock_collection

        service = VectorStoreService()
        results = service.search_similar([0.1] * 384, top_k=5)

        assert len(results) == 2
        assert results[0]['distance'] == 0.2
        assert results[1]['distance'] == 0.35
        mock_collection.query.assert_called_once()

    @patch('rfp_system.services.vector_store.chromadb.PersistentClient')
    def test_delete_chunks(self, mock_client):
        """Test deleting chunks from vector store"""
        mock_collection = Mock()
        mock_client.return_value.get_or_create_collection.return_value = mock_collection

        service = VectorStoreService()
        service.delete_chunks(['chunk_1', 'chunk_2'])

        mock_collection.delete.assert_called_once_with(ids=['chunk_1', 'chunk_2'])


@pytest.mark.unit
class TestGenerationService:
    """Test Claude API integration service"""

    @patch('rfp_system.services.generation.anthropic.Anthropic')
    def test_generate_answer(self, mock_anthropic):
        """Test answer generation with Claude"""
        mock_client = Mock()
        mock_response = Mock()
        mock_content = Mock()
        mock_content.text = "This is a generated answer."
        mock_response.content = [mock_content]
        mock_client.messages.create.return_value = mock_response

        mock_anthropic.return_value = mock_client

        service = GenerationService()
        context_chunks = [
            {'content': 'Context 1', 'similarity': 0.85},
            {'content': 'Context 2', 'similarity': 0.75}
        ]

        result = service.generate_answer(
            question="What is your product?",
            context_chunks=context_chunks
        )

        assert 'answer' in result
        assert result['answer'] == "This is a generated answer."
        assert 'metadata' in result
        mock_client.messages.create.assert_called_once()

    @patch('rfp_system.services.generation.anthropic.Anthropic')
    def test_generate_answer_no_context(self, mock_anthropic):
        """Test answer generation without context (should still work)"""
        mock_client = Mock()
        mock_response = Mock()
        mock_content = Mock()
        mock_content.text = "No sufficient information found."
        mock_response.content = [mock_content]
        mock_client.messages.create.return_value = mock_response

        mock_anthropic.return_value = mock_client

        service = GenerationService()
        result = service.generate_answer(
            question="What is your product?",
            context_chunks=[]
        )

        assert 'answer' in result
        mock_client.messages.create.assert_called_once()

    @patch('rfp_system.services.generation.anthropic.Anthropic')
    def test_api_error_handling(self, mock_anthropic):
        """Test handling of Claude API errors"""
        mock_client = Mock()
        mock_client.messages.create.side_effect = Exception("API Error")
        mock_anthropic.return_value = mock_client

        service = GenerationService()

        with pytest.raises(Exception):
            service.generate_answer("Test question", [])


@pytest.mark.unit
class TestRAGPipeline:
    """Test complete RAG pipeline orchestration"""

    @patch('rfp_system.services.rag_pipeline.EmbeddingService')
    @patch('rfp_system.services.rag_pipeline.VectorStoreService')
    @patch('rfp_system.services.rag_pipeline.GenerationService')
    def test_retrieve_context(self, mock_gen, mock_vector, mock_embed):
        """Test context retrieval from vector store"""
        # Mock embedding service
        mock_embed_instance = Mock()
        mock_embed_instance.generate_embedding.return_value = [0.1] * 384
        mock_embed.return_value = mock_embed_instance

        # Mock vector store service
        mock_vector_instance = Mock()
        mock_vector_instance.search_similar.return_value = [
            {
                'id': 'chunk_1',
                'document': 'Text 1',
                'distance': 0.2,
                'metadata': {'chunk_id': 1}
            },
            {
                'id': 'chunk_2',
                'document': 'Text 2',
                'distance': 0.35,
                'metadata': {'chunk_id': 2}
            }
        ]
        mock_vector.return_value = mock_vector_instance

        pipeline = RAGPipeline()
        results = pipeline.retrieve_context("Test question", top_k=5, similarity_threshold=0.3)

        assert len(results) == 2
        assert results[0]['similarity'] > results[1]['similarity']
        mock_embed_instance.generate_embedding.assert_called_once_with("Test question")

    @patch('rfp_system.services.rag_pipeline.EmbeddingService')
    @patch('rfp_system.services.rag_pipeline.VectorStoreService')
    def test_similarity_threshold_filtering(self, mock_vector, mock_embed):
        """Test that results below similarity threshold are filtered out"""
        mock_embed_instance = Mock()
        mock_embed_instance.generate_embedding.return_value = [0.1] * 384
        mock_embed.return_value = mock_embed_instance

        mock_vector_instance = Mock()
        mock_vector_instance.search_similar.return_value = [
            {'id': 'chunk_1', 'document': 'Text 1', 'distance': 0.2, 'metadata': {}},  # 0.8 similarity
            {'id': 'chunk_2', 'document': 'Text 2', 'distance': 0.8, 'metadata': {}},  # 0.2 similarity
        ]
        mock_vector.return_value = mock_vector_instance

        pipeline = RAGPipeline()
        results = pipeline.retrieve_context("Test", similarity_threshold=0.5)

        # Only chunk_1 should pass (similarity 0.8 > 0.5)
        assert len(results) == 1
        assert results[0]['id'] == 'chunk_1'

    @patch('rfp_system.services.rag_pipeline.EmbeddingService')
    @patch('rfp_system.services.rag_pipeline.VectorStoreService')
    @patch('rfp_system.services.rag_pipeline.GenerationService')
    def test_generate_answer_end_to_end(self, mock_gen, mock_vector, mock_embed):
        """Test complete answer generation pipeline"""
        # Setup mocks
        mock_embed_instance = Mock()
        mock_embed_instance.generate_embedding.return_value = [0.1] * 384
        mock_embed.return_value = mock_embed_instance

        mock_vector_instance = Mock()
        mock_vector_instance.search_similar.return_value = [
            {'id': 'chunk_1', 'document': 'Our product is CRM', 'distance': 0.15, 'metadata': {'chunk_id': 1}}
        ]
        mock_vector.return_value = mock_vector_instance

        mock_gen_instance = Mock()
        mock_gen_instance.generate_answer.return_value = {
            'answer': 'We offer CRM solutions.',
            'metadata': {'model': 'claude-4.5'}
        }
        mock_gen.return_value = mock_gen_instance

        pipeline = RAGPipeline()
        result = pipeline.generate_answer("What is your product?")

        assert 'answer' in result
        assert 'context_chunks' in result
        assert result['answer'] == 'We offer CRM solutions.'
        mock_gen_instance.generate_answer.assert_called_once()
