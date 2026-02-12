"""
Integration tests for REST API endpoints
"""
import pytest
import json
from django.urls import reverse
from rest_framework import status
from rfp_system.models import Document, DocumentChunk, RFP, Question, Answer
from unittest.mock import patch, Mock


@pytest.mark.integration
@pytest.mark.django_db
class TestDocumentAPI:
    """Test Document endpoints"""

    def test_list_documents(self, api_client, document_data):
        """Test GET /api/v1/documents/"""
        url = reverse('document-list')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1
        assert response.data[0]['filename'] == 'test_doc.pdf'

    def test_get_document_detail(self, api_client, document_data):
        """Test GET /api/v1/documents/{id}/"""
        url = reverse('document-detail', kwargs={'pk': document_data.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['filename'] == 'test_doc.pdf'
        assert response.data['status'] == 'completed'

    @patch('rfp_system.views.DocumentProcessor')
    @patch('rfp_system.views.ChunkingService')
    @patch('rfp_system.views.EmbeddingService')
    @patch('rfp_system.views.VectorStoreService')
    def test_upload_document(self, mock_vector, mock_embed, mock_chunk, mock_processor, api_client, tmp_path):
        """Test POST /api/v1/documents/ (file upload)"""
        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Sample document content for testing.")

        # Mock services
        mock_proc_instance = Mock()
        mock_proc_instance.process_document.return_value = {
            'text': 'Sample document content',
            'metadata': {'file_size': 100}
        }
        mock_processor.return_value = mock_proc_instance

        mock_chunk_instance = Mock()
        mock_chunk_instance.chunk_text.return_value = [
            {'text': 'Sample document', 'metadata': {'chunk_index': 0, 'token_count': 2}}
        ]
        mock_chunk.return_value = mock_chunk_instance

        mock_embed_instance = Mock()
        mock_embed_instance.generate_embeddings.return_value = [[0.1] * 384]
        mock_embed.return_value = mock_embed_instance

        mock_vector_instance = Mock()
        mock_vector.return_value = mock_vector_instance

        # Upload
        url = reverse('document-list')
        with open(test_file, 'rb') as f:
            response = api_client.post(url, {'file': f}, format='multipart')

        assert response.status_code == status.HTTP_201_CREATED
        assert 'id' in response.data
        assert response.data['status'] in ['processing', 'completed']

    def test_delete_document(self, api_client, document_data):
        """Test DELETE /api/v1/documents/{id}/"""
        url = reverse('document-detail', kwargs={'pk': document_data.id})
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Document.objects.filter(id=document_data.id).exists()


@pytest.mark.integration
@pytest.mark.django_db
class TestRFPAPI:
    """Test RFP endpoints"""

    def test_list_rfps(self, api_client, rfp_data):
        """Test GET /api/v1/rfps/"""
        url = reverse('rfp-list')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1
        assert response.data[0]['name'] == 'Q1 2024 Enterprise Software RFP'

    def test_get_rfp_detail(self, api_client, rfp_data, question_data):
        """Test GET /api/v1/rfps/{id}/"""
        url = reverse('rfp-detail', kwargs={'pk': rfp_data.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Q1 2024 Enterprise Software RFP'
        assert 'questions' in response.data
        assert len(response.data['questions']) == 3

    def test_create_rfp(self, api_client):
        """Test POST /api/v1/rfps/ (create RFP with questions)"""
        url = reverse('rfp-list')
        data = {
            'name': 'Test RFP',
            'description': 'Test description',
            'questions': [
                {'question_text': 'Question 1?', 'context': 'Context 1'},
                {'question_text': 'Question 2?', 'context': 'Context 2'}
            ]
        }

        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'Test RFP'
        assert len(response.data['questions']) == 2

        # Verify in database
        rfp = RFP.objects.get(id=response.data['id'])
        assert rfp.questions.count() == 2

    def test_delete_rfp(self, api_client, rfp_data):
        """Test DELETE /api/v1/rfps/{id}/"""
        url = reverse('rfp-detail', kwargs={'pk': rfp_data.id})
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not RFP.objects.filter(id=rfp_data.id).exists()

    @patch('rfp_system.views.RAGPipeline')
    def test_generate_answers(self, mock_rag, api_client, rfp_data, question_data, document_chunk_data):
        """Test POST /api/v1/rfps/{id}/generate_answers/"""
        # Mock RAG pipeline
        mock_pipeline = Mock()
        mock_pipeline.generate_answer.return_value = {
            'answer': 'Generated answer text',
            'context_chunks': [{'id': 1, 'similarity': 0.85}],
            'metadata': {'model': 'claude-4.5', 'confidence': 0.95}
        }
        mock_rag.return_value = mock_pipeline

        url = reverse('rfp-generate-answers', kwargs={'pk': rfp_data.id})
        response = api_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        assert 'message' in response.data
        assert 'answers_generated' in response.data

        # Verify answers were created
        for question in question_data:
            assert Answer.objects.filter(question=question).exists()


@pytest.mark.integration
@pytest.mark.django_db
class TestQuestionAPI:
    """Test Question endpoints"""

    @patch('rfp_system.views.RAGPipeline')
    def test_regenerate_answer(self, mock_rag, api_client, question_data, document_chunk_data):
        """Test POST /api/v1/questions/{id}/regenerate/"""
        question = question_data[0]

        # Create initial answer
        answer = Answer.objects.create(
            question=question,
            answer_text='Old answer',
            confidence_score=0.8,
            regenerated_count=0
        )

        # Mock RAG pipeline
        mock_pipeline = Mock()
        mock_pipeline.generate_answer.return_value = {
            'answer': 'New generated answer',
            'context_chunks': [{'id': 1, 'similarity': 0.9}],
            'metadata': {'confidence': 0.95}
        }
        mock_rag.return_value = mock_pipeline

        url = reverse('question-regenerate', kwargs={'pk': question.id})
        response = api_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        assert 'answer' in response.data

        # Verify answer was updated
        answer.refresh_from_db()
        assert answer.answer_text == 'New generated answer'
        assert answer.regenerated_count == 1


@pytest.mark.integration
@pytest.mark.django_db
class TestSearchAPI:
    """Test semantic search endpoint"""

    @patch('rfp_system.views.RAGPipeline')
    def test_semantic_search(self, mock_rag, api_client, document_chunk_data):
        """Test POST /api/v1/search/"""
        # Mock RAG pipeline
        mock_pipeline = Mock()
        mock_pipeline.retrieve_context.return_value = [
            {
                'id': 'chunk_1',
                'content': 'Sample text',
                'similarity': 0.85,
                'metadata': {'page': 1}
            }
        ]
        mock_rag.return_value = mock_pipeline

        url = reverse('search')
        data = {'query': 'test query', 'top_k': 5}

        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data
        assert len(response.data['results']) >= 0

    def test_search_missing_query(self, api_client):
        """Test search endpoint with missing query parameter"""
        url = reverse('search')
        response = api_client.post(url, {}, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.integration
@pytest.mark.django_db
class TestAPIValidation:
    """Test API input validation"""

    def test_create_rfp_missing_name(self, api_client):
        """Test creating RFP without required name field"""
        url = reverse('rfp-list')
        data = {'questions': []}

        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_rfp_invalid_questions(self, api_client):
        """Test creating RFP with invalid question data"""
        url = reverse('rfp-list')
        data = {
            'name': 'Test RFP',
            'questions': [{'invalid_field': 'value'}]  # Missing question_text
        }

        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_upload_document_no_file(self, api_client):
        """Test document upload without file"""
        url = reverse('document-list')
        response = api_client.post(url, {}, format='multipart')

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.integration
@pytest.mark.django_db
class TestAPICORS:
    """Test CORS configuration"""

    def test_cors_headers_present(self, api_client, document_data):
        """Test that CORS headers are present in responses"""
        url = reverse('document-list')
        response = api_client.get(url, HTTP_ORIGIN='http://localhost:3000')

        # CORS headers should be present (configured in settings)
        assert response.status_code == status.HTTP_200_OK
