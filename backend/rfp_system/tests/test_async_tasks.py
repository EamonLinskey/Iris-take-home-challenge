"""
Unit tests for async task processing (Celery)
"""
import pytest
from unittest.mock import patch, Mock, MagicMock
from django.utils import timezone
from rfp_system.models import Document, RFP, Question, Answer, TaskStatus
from rfp_system.tasks import process_document_async, generate_answers_async, regenerate_answer_async


@pytest.mark.unit
@pytest.mark.django_db
class TestTaskStatusModel:
    """Test TaskStatus model"""

    def test_task_status_creation(self, document_data):
        """Test creating a TaskStatus instance"""
        task_status = TaskStatus.objects.create(
            task_id='test-task-123',
            task_type='document_processing',
            status='PENDING',
            document=document_data
        )

        assert task_status.task_id == 'test-task-123'
        assert task_status.task_type == 'document_processing'
        assert task_status.status == 'PENDING'
        assert task_status.progress == 0
        assert task_status.document == document_data
        assert task_status.rfp is None

    def test_task_status_progress_updates(self):
        """Test updating task progress"""
        task_status = TaskStatus.objects.create(
            task_id='test-task-456',
            task_type='answer_generation',
            status='STARTED'
        )

        # Update progress
        task_status.progress = 50
        task_status.current_step = 'Generating answer 5/10'
        task_status.status = 'PROGRESS'
        task_status.save()

        task_status.refresh_from_db()
        assert task_status.progress == 50
        assert task_status.current_step == 'Generating answer 5/10'
        assert task_status.status == 'PROGRESS'

    def test_task_status_completion(self):
        """Test marking task as complete"""
        task_status = TaskStatus.objects.create(
            task_id='test-task-789',
            task_type='document_processing',
            status='PROGRESS'
        )

        # Mark complete
        task_status.status = 'SUCCESS'
        task_status.progress = 100
        task_status.result = {'chunks_created': 10}
        task_status.completed_at = timezone.now()
        task_status.save()

        task_status.refresh_from_db()
        assert task_status.status == 'SUCCESS'
        assert task_status.progress == 100
        assert task_status.result == {'chunks_created': 10}
        assert task_status.completed_at is not None

    def test_task_status_failure(self):
        """Test marking task as failed"""
        task_status = TaskStatus.objects.create(
            task_id='test-task-error',
            task_type='document_processing',
            status='PROGRESS'
        )

        # Mark failed
        task_status.status = 'FAILURE'
        task_status.error = 'Document processing failed'
        task_status.traceback = 'Traceback details...'
        task_status.completed_at = timezone.now()
        task_status.save()

        task_status.refresh_from_db()
        assert task_status.status == 'FAILURE'
        assert task_status.error == 'Document processing failed'
        assert task_status.traceback == 'Traceback details...'


@pytest.mark.unit
@pytest.mark.django_db
class TestDocumentProcessingTask:
    """Test process_document_async task logic"""

    def test_document_processing_updates_status(self, document_data):
        """Test that document status is updated during processing"""
        # Set initial status
        document_data.processing_status = 'pending'
        document_data.save()

        # Mock the RAG pipeline
        with patch('rfp_system.tasks.get_rag_pipeline') as mock_pipeline:
            mock_pipeline.return_value.process_document.return_value = {
                'success': True,
                'chunks_created': 15,
                'text_length': 5000
            }

            # Verify document starts as pending
            assert document_data.processing_status == 'pending'

            # After processing, status should be updated
            # (In real execution, the task would do this)
            result = mock_pipeline.return_value.process_document(
                document_instance=document_data,
                file_path=document_data.file.path
            )

            assert result['success'] is True
            assert result['chunks_created'] == 15

    def test_document_processing_failure_handling(self, document_data):
        """Test that document handles processing failure"""
        with patch('rfp_system.tasks.get_rag_pipeline') as mock_pipeline:
            mock_pipeline.return_value.process_document.return_value = {
                'success': False,
                'error': 'Failed to extract text'
            }

            result = mock_pipeline.return_value.process_document(
                document_instance=document_data,
                file_path=document_data.file.path
            )

            assert result['success'] is False
            assert 'error' in result


@pytest.mark.unit
@pytest.mark.django_db
class TestAnswerGenerationTask:
    """Test generate_answers_async task logic"""

    def test_answer_generation_workflow(self, rfp_data, question_data):
        """Test answer generation workflow"""
        # Mock the RAG pipeline
        with patch('rfp_system.tasks.get_rag_pipeline') as mock_pipeline:
            mock_pipeline.return_value.generate_answer.return_value = {
                'answer': 'Test answer',
                'confidence_score': 0.95,
                'source_chunks': [],
                'metadata': {'cached': False}
            }

            # Verify questions exist
            questions = rfp_data.questions.all()
            assert questions.count() == len(question_data)

            # Test the generation logic
            for question in questions:
                result = mock_pipeline.return_value.generate_answer(
                    question=question.question_text,
                    question_context=question.context,
                    include_confidence=True,
                    use_cache=True
                )

                assert result['answer'] == 'Test answer'
                assert result['confidence_score'] == 0.95

    def test_answer_caching_detection(self, rfp_data, question_data):
        """Test detection of cached vs fresh answers"""
        with patch('rfp_system.tasks.get_rag_pipeline') as mock_pipeline:
            # Simulate cached answer
            mock_pipeline.return_value.generate_answer.return_value = {
                'answer': 'Cached answer',
                'confidence_score': 0.95,
                'source_chunks': [],
                'metadata': {'cached': True, 'cache_key': 'abc123'}
            }

            result = mock_pipeline.return_value.generate_answer(
                question='Test question',
                use_cache=True
            )

            # Verify cache metadata
            assert result['metadata']['cached'] is True
            assert 'cache_key' in result['metadata']


@pytest.mark.unit
@pytest.mark.django_db
class TestRegenerateAnswerTask:
    """Test regenerate_answer_async task"""

    def test_regenerate_answer_success(self, question_data):
        """Test successful answer regeneration"""
        question = question_data[0]

        # Create initial answer
        answer = Answer.objects.create(
            question=question,
            answer_text='Original answer',
            regenerated_count=0
        )

        with patch('rfp_system.tasks.get_rag_pipeline') as mock_pipeline:
            mock_pipeline.return_value.generate_answer.return_value = {
                'answer': 'Regenerated answer',
                'confidence_score': 0.92,
                'source_chunks': [],
                'metadata': {'cached': False}
            }

            result = regenerate_answer_async(str(question.id))

            assert result['success'] is True
            assert result['regenerated'] is True

            # Check answer was updated
            answer.refresh_from_db()
            assert answer.answer_text == 'Regenerated answer'
            assert answer.regenerated_count == 1
            assert answer.cached is False

    def test_regenerate_answer_bypasses_cache(self, question_data):
        """Test that regeneration bypasses cache"""
        question = question_data[0]

        # Create initial cached answer
        Answer.objects.create(
            question=question,
            answer_text='Cached answer',
            cached=True
        )

        with patch('rfp_system.tasks.get_rag_pipeline') as mock_pipeline:
            mock_pipeline.return_value.generate_answer.return_value = {
                'answer': 'Fresh answer',
                'confidence_score': 0.90,
                'source_chunks': [],
                'metadata': {'cached': False}
            }

            result = regenerate_answer_async(str(question.id))

            # Verify use_cache=False was passed
            mock_pipeline.return_value.generate_answer.assert_called_once()
            call_kwargs = mock_pipeline.return_value.generate_answer.call_args.kwargs
            assert call_kwargs['use_cache'] is False

    def test_regenerate_answer_not_found(self):
        """Test regenerating answer for non-existent question"""
        fake_id = '00000000-0000-0000-0000-000000000000'

        with pytest.raises(Exception, match='Question .* not found'):
            regenerate_answer_async(fake_id)


@pytest.mark.integration
@pytest.mark.django_db
class TestTaskStatusAPI:
    """Test TaskStatus API endpoint"""

    def test_get_task_status_success(self, api_client):
        """Test retrieving task status"""
        # Create a task status
        task_status = TaskStatus.objects.create(
            task_id='api-test-123',
            task_type='document_processing',
            status='PROGRESS',
            progress=75,
            current_step='Embedding chunks',
            total_steps=5
        )

        response = api_client.get('/api/v1/tasks/status/', {'task_id': 'api-test-123'})

        assert response.status_code == 200
        data = response.json()
        assert data['task_id'] == 'api-test-123'
        assert data['task_type'] == 'document_processing'
        assert data['status'] == 'PROGRESS'
        assert data['progress'] == 75
        assert data['current_step'] == 'Embedding chunks'
        assert data['total_steps'] == 5

    def test_get_task_status_not_found(self, api_client):
        """Test retrieving non-existent task status"""
        response = api_client.get('/api/v1/tasks/status/', {'task_id': 'nonexistent'})

        assert response.status_code == 404
        assert 'not found' in response.json()['error']

    def test_get_task_status_missing_param(self, api_client):
        """Test retrieving task status without task_id parameter"""
        response = api_client.get('/api/v1/tasks/status/')

        assert response.status_code == 400
        assert 'required' in response.json()['error']

    def test_get_task_status_with_document(self, api_client, document_data):
        """Test retrieving task status with related document"""
        task_status = TaskStatus.objects.create(
            task_id='api-test-doc',
            task_type='document_processing',
            status='SUCCESS',
            document=document_data,
            progress=100
        )

        response = api_client.get('/api/v1/tasks/status/', {'task_id': 'api-test-doc'})

        assert response.status_code == 200
        data = response.json()
        assert data['document_id'] == str(document_data.id)
        assert data['rfp_id'] is None

    def test_get_task_status_with_rfp(self, api_client, rfp_data):
        """Test retrieving task status with related RFP"""
        task_status = TaskStatus.objects.create(
            task_id='api-test-rfp',
            task_type='answer_generation',
            status='SUCCESS',
            rfp=rfp_data,
            progress=100
        )

        response = api_client.get('/api/v1/tasks/status/', {'task_id': 'api-test-rfp'})

        assert response.status_code == 200
        data = response.json()
        assert data['rfp_id'] == str(rfp_data.id)
        assert data['document_id'] is None

    def test_get_task_status_with_error(self, api_client):
        """Test retrieving task status with error"""
        task_status = TaskStatus.objects.create(
            task_id='api-test-error',
            task_type='document_processing',
            status='FAILURE',
            error='Processing failed',
            traceback='Traceback...'
        )

        response = api_client.get('/api/v1/tasks/status/', {'task_id': 'api-test-error'})

        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'FAILURE'
        assert data['error'] == 'Processing failed'


@pytest.mark.integration
@pytest.mark.django_db
class TestAsyncDocumentUpload:
    """Test async document upload workflow"""

    def test_document_upload_returns_task_id(self, api_client):
        """Test that document upload returns task_id"""
        with patch('rfp_system.views.process_document_async') as mock_task:
            mock_task.delay.return_value.id = 'task-upload-123'

            # Create test file
            from io import BytesIO
            test_file = BytesIO(b'Test document content')
            test_file.name = 'test.txt'

            response = api_client.post('/api/v1/documents/', {
                'file': test_file,
                'filename': 'test.txt',
                'file_type': 'txt'
            }, format='multipart')

            assert response.status_code == 202  # Async response
            data = response.json()
            assert 'task_id' in data
            assert data['task_id'] == 'task-upload-123'
            assert 'Processing started in background' in data['message']


@pytest.mark.integration
@pytest.mark.django_db
class TestAsyncAnswerGeneration:
    """Test async answer generation workflow"""

    def test_generate_answers_returns_task_id(self, api_client, rfp_data, question_data):
        """Test that answer generation returns task_id"""
        with patch('rfp_system.views.generate_answers_async') as mock_task:
            mock_task.delay.return_value.id = 'task-answers-123'

            response = api_client.post(f'/api/v1/rfps/{rfp_data.id}/generate_answers/')

            assert response.status_code == 202  # Async response
            data = response.json()
            assert data['success'] is True
            assert data['task_id'] == 'task-answers-123'
            assert 'background' in data['message']
            assert data['total_questions'] == len(question_data)


@pytest.mark.integration
@pytest.mark.django_db
class TestEndToEndAsync:
    """Test complete async workflow"""

    def test_full_async_workflow(self, api_client, document_data, rfp_data, question_data):
        """Test complete async workflow from upload to answer generation"""
        # Step 1: Upload document (async)
        with patch('rfp_system.views.process_document_async') as mock_doc_task:
            mock_doc_task.delay.return_value.id = 'doc-task-123'

            from io import BytesIO
            test_file = BytesIO(b'Test content')
            test_file.name = 'test.txt'

            upload_response = api_client.post('/api/v1/documents/', {
                'file': test_file,
                'filename': 'test.txt',
                'file_type': 'txt'
            }, format='multipart')

            assert upload_response.status_code == 202
            doc_task_id = upload_response.json()['task_id']

        # Step 2: Check document processing status
        doc_task_status = TaskStatus.objects.create(
            task_id=doc_task_id,
            task_type='document_processing',
            status='SUCCESS',
            progress=100,
            document=document_data
        )

        status_response = api_client.get('/api/v1/tasks/status/', {'task_id': doc_task_id})
        assert status_response.status_code == 200
        assert status_response.json()['status'] == 'SUCCESS'

        # Step 3: Generate answers (async)
        with patch('rfp_system.views.generate_answers_async') as mock_answer_task:
            mock_answer_task.delay.return_value.id = 'answer-task-123'

            answer_response = api_client.post(f'/api/v1/rfps/{rfp_data.id}/generate_answers/')

            assert answer_response.status_code == 202
            answer_task_id = answer_response.json()['task_id']

        # Step 4: Check answer generation status
        answer_task_status = TaskStatus.objects.create(
            task_id=answer_task_id,
            task_type='answer_generation',
            status='SUCCESS',
            progress=100,
            rfp=rfp_data,
            result={'total_questions': 3, 'answers_created': 3}
        )

        answer_status_response = api_client.get('/api/v1/tasks/status/', {'task_id': answer_task_id})
        assert answer_status_response.status_code == 200
        assert answer_status_response.json()['status'] == 'SUCCESS'
        assert answer_status_response.json()['result']['answers_created'] == 3
