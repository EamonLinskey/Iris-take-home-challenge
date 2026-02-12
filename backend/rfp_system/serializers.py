"""
Django REST Framework serializers for RFP system
"""
from rest_framework import serializers
from .models import Document, DocumentChunk, RFP, Question, Answer


class DocumentChunkSerializer(serializers.ModelSerializer):
    """Serializer for document chunks"""

    class Meta:
        model = DocumentChunk
        fields = [
            'id', 'chunk_index', 'content', 'chromadb_id',
            'chunk_metadata', 'created_at'
        ]
        read_only_fields = ['id', 'chromadb_id', 'created_at']


class DocumentSerializer(serializers.ModelSerializer):
    """Serializer for documents"""
    chunks = DocumentChunkSerializer(many=True, read_only=True)

    class Meta:
        model = Document
        fields = [
            'id', 'filename', 'file_type', 'file', 'uploaded_at',
            'processed', 'processing_status', 'chunk_count',
            'metadata', 'chunks'
        ]
        read_only_fields = [
            'id', 'uploaded_at', 'processed', 'processing_status',
            'chunk_count', 'metadata'
        ]


class DocumentListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for document lists (without chunks)"""

    class Meta:
        model = Document
        fields = [
            'id', 'filename', 'file_type', 'uploaded_at',
            'processed', 'processing_status', 'chunk_count'
        ]
        read_only_fields = fields


class AnswerSerializer(serializers.ModelSerializer):
    """Serializer for answers"""
    source_chunks = DocumentChunkSerializer(many=True, read_only=True)
    question_text = serializers.CharField(source='question.question_text', read_only=True)

    class Meta:
        model = Answer
        fields = [
            'id', 'question', 'question_text', 'answer_text',
            'source_chunks', 'confidence_score', 'generated_at',
            'regenerated_count', 'cached', 'metadata'
        ]
        read_only_fields = [
            'id', 'generated_at', 'regenerated_count',
            'cached', 'metadata'
        ]


class QuestionSerializer(serializers.ModelSerializer):
    """Serializer for questions"""
    answer = AnswerSerializer(read_only=True)

    class Meta:
        model = Question
        fields = [
            'id', 'rfp', 'question_number', 'question_text',
            'context', 'created_at', 'answer'
        ]
        read_only_fields = ['id', 'created_at']


class QuestionCreateSerializer(serializers.Serializer):
    """Serializer for creating questions (used in RFP creation)"""
    question_number = serializers.IntegerField()
    question_text = serializers.CharField()
    context = serializers.CharField(required=False, allow_blank=True)


class RFPSerializer(serializers.ModelSerializer):
    """Serializer for RFPs"""
    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = RFP
        fields = [
            'id', 'name', 'description', 'uploaded_at',
            'status', 'questions'
        ]
        read_only_fields = ['id', 'uploaded_at', 'status']


class RFPCreateSerializer(serializers.Serializer):
    """Serializer for creating RFPs with questions"""
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    questions = QuestionCreateSerializer(many=True)

    def create(self, validated_data):
        """Create RFP with questions"""
        questions_data = validated_data.pop('questions')

        # Create RFP
        rfp = RFP.objects.create(**validated_data)

        # Create questions
        for question_data in questions_data:
            Question.objects.create(rfp=rfp, **question_data)

        return rfp


class RFPListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for RFP lists"""
    question_count = serializers.IntegerField(source='questions.count', read_only=True)

    class Meta:
        model = RFP
        fields = ['id', 'name', 'description', 'uploaded_at', 'status', 'question_count']
        read_only_fields = fields


class SearchQuerySerializer(serializers.Serializer):
    """Serializer for semantic search requests"""
    query = serializers.CharField()
    top_k = serializers.IntegerField(default=5, min_value=1, max_value=20)
    similarity_threshold = serializers.FloatField(default=0.3, min_value=0.0, max_value=1.0)


class SearchResultSerializer(serializers.Serializer):
    """Serializer for search results"""
    chunk_id = serializers.CharField()
    content = serializers.CharField()
    similarity = serializers.FloatField()
    metadata = serializers.JSONField()


class AnswerGenerationSerializer(serializers.Serializer):
    """Serializer for answer generation parameters"""
    include_confidence = serializers.BooleanField(default=True)
    top_k = serializers.IntegerField(default=5, min_value=1, max_value=20)
