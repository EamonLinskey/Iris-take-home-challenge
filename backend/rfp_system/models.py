from django.db import models
import uuid


class Document(models.Model):
    """Company knowledge base documents"""

    FILE_TYPE_CHOICES = [
        ('pdf', 'PDF'),
        ('docx', 'DOCX'),
        ('txt', 'TXT'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    filename = models.CharField(max_length=255)
    file_type = models.CharField(max_length=10, choices=FILE_TYPE_CHOICES)
    file = models.FileField(upload_to='documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)
    processing_status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')
    chunk_count = models.IntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.filename} ({self.processing_status})"


class DocumentChunk(models.Model):
    """Text chunks from documents for RAG retrieval"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='chunks')
    chunk_index = models.IntegerField()
    content = models.TextField()
    chunk_metadata = models.JSONField(default=dict, blank=True)  # page_num, section, etc.
    chromadb_id = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['document', 'chunk_index']
        unique_together = ['document', 'chunk_index']

    def __str__(self):
        return f"Chunk {self.chunk_index} from {self.document.filename}"


class RFP(models.Model):
    """RFP (Request for Proposal) submissions"""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')

    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = 'RFP'
        verbose_name_plural = 'RFPs'

    def __str__(self):
        return f"{self.name} ({self.status})"


class Question(models.Model):
    """Individual questions from RFPs"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rfp = models.ForeignKey(RFP, on_delete=models.CASCADE, related_name='questions')
    question_number = models.IntegerField()
    question_text = models.TextField()
    context = models.TextField(blank=True)  # Additional context if provided
    question_hash = models.CharField(max_length=64, blank=True, db_index=True)  # For answer caching
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['rfp', 'question_number']
        unique_together = ['rfp', 'question_number']

    def __str__(self):
        return f"Q{self.question_number}: {self.question_text[:50]}..."

    def save(self, *args, **kwargs):
        """Auto-generate question hash on save"""
        if not self.question_hash:
            from .services.caching import generate_question_hash
            self.question_hash = generate_question_hash(self.question_text)
        super().save(*args, **kwargs)


class Answer(models.Model):
    """Generated answers to RFP questions"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.OneToOneField(Question, on_delete=models.CASCADE, related_name='answer')
    answer_text = models.TextField()
    source_chunks = models.ManyToManyField(DocumentChunk, related_name='answers', blank=True)
    confidence_score = models.FloatField(null=True, blank=True)  # Stretch feature
    generated_at = models.DateTimeField(auto_now_add=True)
    regenerated_count = models.IntegerField(default=0)
    cached = models.BooleanField(default=False)  # Stretch feature
    metadata = models.JSONField(default=dict, blank=True)  # prompt tokens, model info, etc.

    class Meta:
        ordering = ['-generated_at']

    def __str__(self):
        return f"Answer to: {self.question.question_text[:50]}..."
