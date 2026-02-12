"""
Unit tests for Django models
"""
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rfp_system.models import Document, DocumentChunk, RFP, Question, Answer


@pytest.mark.unit
@pytest.mark.django_db
class TestDocumentModel:
    """Test Document model"""

    def test_create_document(self):
        """Test creating a document"""
        file = SimpleUploadedFile("test.pdf", b"content", content_type="application/pdf")
        doc = Document.objects.create(
            filename='test.pdf',
            file_type='pdf',
            file=file,
            processing_status='processing'
        )

        assert doc.id is not None
        assert doc.filename == 'test.pdf'
        assert doc.processing_status == 'processing'
        assert 'test.pdf' in str(doc)

    def test_document_status_choices(self):
        """Test document status field accepts valid choices"""
        valid_statuses = ['pending', 'processing', 'completed', 'failed']

        for status_val in valid_statuses:
            file = SimpleUploadedFile(f"test_{status_val}.pdf", b"content")
            doc = Document.objects.create(
                filename=f'test_{status_val}.pdf',
                file_type='pdf',
                file=file,
                processing_status=status_val
            )
            assert doc.processing_status == status_val

    def test_document_metadata_field(self):
        """Test metadata JSON field"""
        metadata = {
            'page_count': 10,
            'author': 'Test Author'
        }

        file = SimpleUploadedFile("test.pdf", b"content")
        doc = Document.objects.create(
            filename='test.pdf',
            file_type='pdf',
            file=file,
            metadata=metadata
        )

        assert doc.metadata['page_count'] == 10
        assert doc.metadata['author'] == 'Test Author'

    def test_document_timestamps(self):
        """Test auto-generated timestamps"""
        file = SimpleUploadedFile("test.pdf", b"content")
        doc = Document.objects.create(
            filename='test.pdf',
            file_type='pdf',
            file=file
        )

        assert doc.uploaded_at is not None


@pytest.mark.unit
@pytest.mark.django_db
class TestDocumentChunkModel:
    """Test DocumentChunk model"""

    def test_create_chunk(self, document_data):
        """Test creating a document chunk"""
        chunk = DocumentChunk.objects.create(
            document=document_data,
            content='Sample chunk content',
            chunk_index=10,
            chromadb_id='chunk_unique_id_10',
            chunk_metadata={'page': 1}
        )

        assert chunk.id is not None
        assert chunk.document == document_data
        assert chunk.chunk_index == 10
        assert chunk.chromadb_id == 'chunk_unique_id_10'

    def test_chunk_ordering(self, document_data):
        """Test chunks are ordered by document and chunk_index"""
        chunk1 = DocumentChunk.objects.create(
            document=document_data,
            content='Chunk 1',
            chunk_index=10,
            chromadb_id='chunk_10'
        )
        chunk2 = DocumentChunk.objects.create(
            document=document_data,
            content='Chunk 2',
            chunk_index=11,
            chromadb_id='chunk_11'
        )

        chunks = list(DocumentChunk.objects.filter(document=document_data, chunk_index__gte=10))
        assert chunks[0] == chunk1
        assert chunks[1] == chunk2

    def test_chunk_deletion_cascades(self, document_data, document_chunk_data):
        """Test that deleting document deletes its chunks"""
        chunk_ids = [chunk.id for chunk in document_chunk_data]

        document_data.delete()

        for chunk_id in chunk_ids:
            assert not DocumentChunk.objects.filter(id=chunk_id).exists()

    def test_chunk_metadata(self, document_data):
        """Test chunk metadata field"""
        chunk = DocumentChunk.objects.create(
            document=document_data,
            content='Test',
            chunk_index=20,
            chromadb_id='test_chunk_20',
            chunk_metadata={'page': 1, 'section': 'intro'}
        )

        assert chunk.chunk_metadata['page'] == 1
        assert chunk.chunk_metadata['section'] == 'intro'


@pytest.mark.unit
@pytest.mark.django_db
class TestRFPModel:
    """Test RFP model"""

    def test_create_rfp(self):
        """Test creating an RFP"""
        rfp = RFP.objects.create(
            name='Test RFP',
            description='Test description',
            status='pending'
        )

        assert rfp.id is not None
        assert rfp.name == 'Test RFP'
        assert 'Test RFP' in str(rfp)

    def test_rfp_status_choices(self):
        """Test RFP status field"""
        valid_statuses = ['pending', 'processing', 'completed', 'failed']

        for status_val in valid_statuses:
            rfp = RFP.objects.create(
                name=f'RFP {status_val}',
                status=status_val
            )
            assert rfp.status == status_val

    def test_rfp_question_count(self, rfp_data, question_data):
        """Test counting questions in an RFP"""
        count = rfp_data.questions.count()
        assert count == 3


@pytest.mark.unit
@pytest.mark.django_db
class TestQuestionModel:
    """Test Question model"""

    def test_create_question(self, rfp_data):
        """Test creating a question"""
        question = Question.objects.create(
            rfp=rfp_data,
            question_text='What is your product?',
            question_number=10,
            context='Additional context'
        )

        assert question.id is not None
        assert question.rfp == rfp_data
        assert question.question_number == 10

    def test_question_ordering(self, rfp_data):
        """Test questions are ordered by rfp and question_number"""
        q1 = Question.objects.create(
            rfp=rfp_data,
            question_text='Question 1',
            question_number=20
        )
        q2 = Question.objects.create(
            rfp=rfp_data,
            question_text='Question 2',
            question_number=21
        )

        questions = list(Question.objects.filter(rfp=rfp_data, question_number__gte=20))
        assert questions[0] == q1
        assert questions[1] == q2

    def test_question_deletion_cascades(self, rfp_data, question_data):
        """Test that deleting RFP deletes its questions"""
        question_ids = [q.id for q in question_data]

        rfp_data.delete()

        for q_id in question_ids:
            assert not Question.objects.filter(id=q_id).exists()


@pytest.mark.unit
@pytest.mark.django_db
class TestAnswerModel:
    """Test Answer model"""

    def test_create_answer(self, question_data):
        """Test creating an answer"""
        question = question_data[0]
        answer = Answer.objects.create(
            question=question,
            answer_text='This is the answer.',
            confidence_score=0.95,
            regenerated_count=0
        )

        assert answer.id is not None
        assert answer.question == question
        assert answer.confidence_score == 0.95
        assert answer.regenerated_count == 0

    def test_answer_source_chunks(self, question_data, document_chunk_data):
        """Test answer with source chunks (many-to-many)"""
        question = question_data[0]
        answer = Answer.objects.create(
            question=question,
            answer_text='Answer with sources',
            confidence_score=0.9
        )

        answer.source_chunks.add(*document_chunk_data[:2])

        assert answer.source_chunks.count() == 2
        assert document_chunk_data[0] in answer.source_chunks.all()

    def test_answer_metadata(self, question_data):
        """Test answer metadata field"""
        question = question_data[0]
        metadata = {
            'model': 'claude-4.5',
            'tokens': 150
        }

        answer = Answer.objects.create(
            question=question,
            answer_text='Test',
            metadata=metadata
        )

        assert answer.metadata['model'] == 'claude-4.5'
        assert answer.metadata['tokens'] == 150

    def test_answer_regeneration_count(self, question_data):
        """Test incrementing regeneration count"""
        question = question_data[0]
        answer = Answer.objects.create(
            question=question,
            answer_text='First answer',
            regenerated_count=0
        )

        # Simulate regeneration
        answer.regenerated_count += 1
        answer.answer_text = 'Regenerated answer'
        answer.save()

        answer.refresh_from_db()
        assert answer.regenerated_count == 1
        assert answer.answer_text == 'Regenerated answer'

    def test_answer_deletion_cascades(self, question_data):
        """Test that deleting question deletes its answer"""
        question = question_data[0]
        answer = Answer.objects.create(
            question=question,
            answer_text='Test answer'
        )
        answer_id = answer.id

        question.delete()

        assert not Answer.objects.filter(id=answer_id).exists()

    def test_confidence_score_range(self, question_data):
        """Test confidence score is between 0 and 1"""
        question = question_data[0]

        # Valid scores
        for i, score in enumerate([0.0, 0.5, 1.0]):
            # Need different questions for each answer (OneToOne relationship)
            q = Question.objects.create(
                rfp=question.rfp,
                question_text=f'Question for score {score}',
                question_number=100 + i  # Use sequential numbers far from existing ones
            )
            answer = Answer.objects.create(
                question=q,
                answer_text=f'Answer {score}',
                confidence_score=score
            )
            assert 0.0 <= answer.confidence_score <= 1.0
