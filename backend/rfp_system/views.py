"""
Django REST Framework views for RFP system API
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404

from .models import Document, DocumentChunk, RFP, Question, Answer, TaskStatus
from .serializers import (
    DocumentSerializer, DocumentListSerializer, DocumentChunkSerializer,
    RFPSerializer, RFPListSerializer, RFPCreateSerializer,
    QuestionSerializer, AnswerSerializer,
    SearchQuerySerializer, SearchResultSerializer,
    AnswerGenerationSerializer
)
from .services.rag_pipeline import get_rag_pipeline
from .tasks import process_document_async, generate_answers_async, regenerate_answer_async


class DocumentViewSet(viewsets.ModelViewSet):
    """
    API endpoints for document management

    list: Get all documents
    create: Upload a new document (will be processed automatically)
    retrieve: Get document details with chunks
    destroy: Delete a document and its chunks
    """
    queryset = Document.objects.all()
    parser_classes = [MultiPartParser, FormParser]

    def get_serializer_class(self):
        """Use lightweight serializer for list view"""
        if self.action == 'list':
            return DocumentListSerializer
        return DocumentSerializer

    def perform_create(self, serializer):
        """Save document and trigger async processing"""
        document = serializer.save()

        # Dispatch async task for document processing
        task = process_document_async.delay(str(document.id))

        # Store task info for response
        self.task_id = task.id
        self.document_id = str(document.id)

    def create(self, request, *args, **kwargs):
        """Override create to include task info"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)

        # Include task info for async processing
        response_data = serializer.data
        response_data['task_id'] = getattr(self, 'task_id', None)
        response_data['message'] = 'Document uploaded successfully. Processing started in background.'

        return Response(
            response_data,
            status=status.HTTP_202_ACCEPTED,  # 202 for async processing
            headers=headers
        )

    def perform_destroy(self, instance):
        """Delete document and its vector data"""
        rag_pipeline = get_rag_pipeline()
        rag_pipeline.delete_document_data(str(instance.id))
        instance.delete()


class RFPViewSet(viewsets.ModelViewSet):
    """
    API endpoints for RFP management

    list: Get all RFPs
    create: Create new RFP with questions
    retrieve: Get RFP details with questions and answers
    generate_answers: Generate answers for all questions in RFP
    """
    queryset = RFP.objects.all()

    def get_serializer_class(self):
        """Use appropriate serializer based on action"""
        if self.action == 'list':
            return RFPListSerializer
        elif self.action == 'create':
            return RFPCreateSerializer
        return RFPSerializer

    @action(detail=True, methods=['post'])
    def generate_answers(self, request, pk=None):
        """
        Generate answers for all questions in this RFP (async)

        POST /api/v1/rfps/{id}/generate-answers/
        Body: {
            "include_confidence": true,  # optional, default true
            "top_k": 5  # optional, default 5
        }

        Returns task_id for tracking progress
        """
        rfp = self.get_object()

        # Dispatch async task for answer generation
        task = generate_answers_async.delay(str(rfp.id))

        return Response({
            'success': True,
            'rfp_id': str(rfp.id),
            'task_id': task.id,
            'message': 'Answer generation started in background. Use task_id to check progress.',
            'total_questions': rfp.questions.count()
        }, status=status.HTTP_202_ACCEPTED)


class QuestionViewSet(viewsets.ModelViewSet):
    """
    API endpoints for question management

    list: Get all questions
    retrieve: Get question details with answer
    regenerate_answer: Regenerate answer for a specific question
    """
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer

    @action(detail=True, methods=['post'])
    def regenerate_answer(self, request, pk=None):
        """
        Regenerate answer for a specific question

        POST /api/v1/questions/{id}/regenerate-answer/
        Body: {
            "include_confidence": true,  # optional
            "top_k": 5  # optional
        }
        """
        question = self.get_object()

        # Parse parameters
        param_serializer = AnswerGenerationSerializer(data=request.data)
        param_serializer.is_valid(raise_exception=True)
        params = param_serializer.validated_data

        try:
            rag_pipeline = get_rag_pipeline()

            # Generate new answer
            result = rag_pipeline.generate_answer(
                question=question.question_text,
                question_context=question.context,
                include_confidence=params['include_confidence'],
                top_k=params['top_k']
            )

            # Check if this answer came from cache
            is_cached = result.get('metadata', {}).get('cached', False)

            # Update or create answer
            answer, created = Answer.objects.get_or_create(
                question=question,
                defaults={
                    'answer_text': result['answer'],
                    'confidence_score': result.get('confidence_score'),
                    'metadata': result['metadata'],
                    'cached': is_cached
                }
            )

            if not created:
                answer.answer_text = result['answer']
                answer.confidence_score = result.get('confidence_score')
                answer.metadata = result['metadata']
                answer.cached = is_cached
                answer.regenerated_count += 1
                answer.save()

            # Link source chunks
            chunk_ids = [chunk['id'] for chunk in result.get('source_chunks', [])]
            if chunk_ids:
                chunks = DocumentChunk.objects.filter(chromadb_id__in=chunk_ids)
                answer.source_chunks.set(chunks)

            # Serialize and return
            serializer = AnswerSerializer(answer)
            return Response({
                'success': True,
                'answer': serializer.data
            })

        except Exception as e:
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AnswerViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoints for viewing answers (read-only)

    list: Get all answers
    retrieve: Get answer details with source chunks
    """
    queryset = Answer.objects.all()
    serializer_class = AnswerSerializer


class SearchViewSet(viewsets.ViewSet):
    """
    API endpoint for testing semantic search

    search: Test semantic search against document chunks
    """

    @action(detail=False, methods=['post'])
    def search(self, request):
        """
        Perform semantic search

        POST /api/v1/search/
        Body: {
            "query": "What are the company's core values?",
            "top_k": 5,  # optional
            "similarity_threshold": 0.7  # optional
        }
        """
        # Validate request
        serializer = SearchQuerySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        params = serializer.validated_data

        try:
            rag_pipeline = get_rag_pipeline()

            # Perform search
            results = rag_pipeline.retrieve_context(
                question=params['query'],
                top_k=params['top_k'],
                similarity_threshold=params['similarity_threshold']
            )

            # Format results
            formatted_results = []
            for chunk in results:
                formatted_results.append({
                    'chunk_id': chunk['id'],
                    'content': chunk['content'],
                    'similarity': chunk['similarity'],
                    'metadata': chunk['metadata']
                })

            return Response({
                'query': params['query'],
                'results': formatted_results,
                'count': len(formatted_results)
            })

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TaskStatusViewSet(viewsets.ViewSet):
    """
    API endpoint for checking async task status

    status: Get status of a background task
    """

    @action(detail=False, methods=['get'])
    def status(self, request):
        """
        Get status of a background task

        GET /api/v1/tasks/status/?task_id=<task_id>
        """
        task_id = request.query_params.get('task_id')

        if not task_id:
            return Response(
                {'error': 'task_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Get task status from database
            task_status = TaskStatus.objects.get(task_id=task_id)

            return Response({
                'task_id': task_status.task_id,
                'task_type': task_status.task_type,
                'status': task_status.status,
                'progress': task_status.progress,
                'current_step': task_status.current_step,
                'total_steps': task_status.total_steps,
                'result': task_status.result,
                'error': task_status.error,
                'created_at': task_status.created_at,
                'started_at': task_status.started_at,
                'completed_at': task_status.completed_at,
                'document_id': str(task_status.document.id) if task_status.document else None,
                'rfp_id': str(task_status.rfp.id) if task_status.rfp else None,
            })

        except TaskStatus.DoesNotExist:
            return Response(
                {'error': f'Task {task_id} not found'},
                status=status.HTTP_404_NOT_FOUND
            )
