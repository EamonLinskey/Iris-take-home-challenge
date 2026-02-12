"""
Shared test fixtures and configuration for pytest
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from unittest.mock import Mock, patch
from django.core.files.uploadedfile import SimpleUploadedFile

User = get_user_model()


@pytest.fixture
def api_client():
    """DRF API client for testing endpoints"""
    return APIClient()


@pytest.fixture
def admin_user(db):
    """Create an admin user for testing"""
    return User.objects.create_superuser(
        username='testadmin',
        email='admin@test.com',
        password='testpass123'
    )


@pytest.fixture
def sample_text():
    """Sample text for testing document processing"""
    return """
    Company Overview

    Our company specializes in enterprise software solutions.
    We have over 10 years of experience in the industry.

    Core Services

    We provide cloud-based SaaS platforms for businesses.
    Our main products include CRM, project management, and analytics tools.

    Security & Compliance

    We are SOC 2 Type II certified and GDPR compliant.
    All data is encrypted at rest and in transit.
    """


@pytest.fixture
def sample_pdf_path(tmp_path):
    """Create a temporary PDF file for testing"""
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter

    pdf_path = tmp_path / "test_document.pdf"
    c = canvas.Canvas(str(pdf_path), pagesize=letter)
    c.drawString(100, 750, "Test Document")
    c.drawString(100, 730, "This is a test PDF for unit testing.")
    c.drawString(100, 710, "It contains sample content about our company.")
    c.save()

    return str(pdf_path)


@pytest.fixture
def mock_embeddings():
    """Mock embedding model to avoid loading actual model"""
    with patch('rfp_system.services.embedding.SentenceTransformer') as mock:
        mock_model = Mock()
        mock_model.encode.return_value = [[0.1] * 384]  # 384-dim vector
        mock.return_value = mock_model
        yield mock_model


@pytest.fixture
def mock_chroma_client():
    """Mock ChromaDB client to avoid actual vector storage"""
    with patch('rfp_system.services.vector_store.chromadb.PersistentClient') as mock:
        mock_client = Mock()
        mock_collection = Mock()

        # Mock collection methods
        mock_collection.add.return_value = None
        mock_collection.query.return_value = {
            'ids': [['chunk_1', 'chunk_2']],
            'distances': [[0.2, 0.35]],
            'documents': [['Sample text 1', 'Sample text 2']],
            'metadatas': [[{'chunk_id': 1}, {'chunk_id': 2}]]
        }
        mock_collection.delete.return_value = None

        mock_client.get_or_create_collection.return_value = mock_collection
        mock.return_value = mock_client

        yield mock_client


@pytest.fixture
def mock_claude_api():
    """Mock Claude API client to avoid actual API calls"""
    with patch('rfp_system.services.generation.anthropic.Anthropic') as mock:
        mock_client = Mock()
        mock_response = Mock()
        mock_message = Mock()

        # Mock successful response
        mock_message.content = [Mock(text="""Our company has extensive experience with enterprise software,
        having developed cloud-based SaaS platforms for over 10 years. We specialize in CRM, project management,
        and analytics tools for businesses.""")]
        mock_response.id = 'msg_test123'
        mock_response.content = mock_message.content

        mock_client.messages.create.return_value = mock_response
        mock.return_value = mock_client

        yield mock_client


@pytest.fixture
def document_data(db):
    """Create a sample Document in the database"""
    from rfp_system.models import Document

    file = SimpleUploadedFile("test.txt", b"Test content", content_type="text/plain")
    return Document.objects.create(
        filename='test_doc.txt',
        file_type='txt',
        file=file,
        processing_status='completed',
        processed=True,
        chunk_count=1,
        metadata={'test': True}
    )


@pytest.fixture
def document_chunk_data(db, document_data):
    """Create sample DocumentChunks in the database"""
    from rfp_system.models import DocumentChunk

    chunks = []
    texts = [
        "Our company specializes in enterprise software solutions with over 10 years of experience.",
        "We provide cloud-based SaaS platforms including CRM, project management, and analytics tools.",
        "We are SOC 2 Type II certified and GDPR compliant with full encryption."
    ]

    for i, text in enumerate(texts):
        chunk = DocumentChunk.objects.create(
            document=document_data,
            content=text,
            chunk_index=i,
            chromadb_id=f'chunk_{document_data.id}_{i}',
            chunk_metadata={'page': 1}
        )
        chunks.append(chunk)

    return chunks


@pytest.fixture
def rfp_data(db):
    """Create a sample RFP in the database"""
    from rfp_system.models import RFP

    return RFP.objects.create(
        name='Q1 2024 Enterprise Software RFP',
        description='Test RFP for enterprise software procurement',
        status='pending'
    )


@pytest.fixture
def question_data(db, rfp_data):
    """Create sample Questions in the database"""
    from rfp_system.models import Question

    questions = []
    question_texts = [
        "What is your company's experience with enterprise software?",
        "Describe your security and compliance certifications.",
        "What are your main product offerings?"
    ]

    for i, text in enumerate(question_texts):
        question = Question.objects.create(
            rfp=rfp_data,
            question_text=text,
            question_number=i,
            context=f"Context for question {i+1}"
        )
        questions.append(question)

    return questions
