"""
Celery tasks for async processing
"""
from celery import shared_task
from django.utils import timezone
from .models import Document, RFP, Question, Answer, TaskStatus
from .services.rag_pipeline import get_rag_pipeline
import traceback as tb


@shared_task(bind=True)
def process_document_async(self, document_id: str):
    """
    Async task to process a document (extract, chunk, embed, store)

    Args:
        document_id: UUID of the document to process

    Returns:
        dict: Processing results
    """
    task_status = None

    try:
        # Get document
        document = Document.objects.get(id=document_id)

        # Create task status record
        task_status = TaskStatus.objects.create(
            task_id=self.request.id,
            task_type='document_processing',
            status='STARTED',
            document=document,
            total_steps=5
        )
        task_status.started_at = timezone.now()
        task_status.save()

        # Update document status
        document.processing_status = 'processing'
        document.save()

        # Step 1: Initialize
        task_status.progress = 10
        task_status.current_step = 'Initializing document processing'
        task_status.save()

        # Step 2: Extract text
        task_status.progress = 20
        task_status.current_step = 'Extracting text from document'
        task_status.save()

        # Get RAG pipeline
        pipeline = get_rag_pipeline()

        # Step 3: Process document (chunk, embed, store)
        task_status.progress = 40
        task_status.current_step = 'Chunking and embedding document'
        task_status.save()

        result = pipeline.process_document(
            document_instance=document,
            file_path=document.file.path
        )

        # Step 4: Finalize
        task_status.progress = 90
        task_status.current_step = 'Finalizing processing'
        task_status.save()

        if result['success']:
            # Success
            task_status.status = 'SUCCESS'
            task_status.progress = 100
            task_status.current_step = 'Complete'
            task_status.result = result
            task_status.completed_at = timezone.now()
            task_status.save()

            return {
                'success': True,
                'document_id': str(document_id),
                'chunks_created': result.get('chunks_created', 0),
                'text_length': result.get('text_length', 0)
            }
        else:
            # Processing failed
            raise Exception(result.get('error', 'Unknown processing error'))

    except Document.DoesNotExist:
        error_msg = f"Document {document_id} not found"
        if task_status:
            task_status.status = 'FAILURE'
            task_status.error = error_msg
            task_status.completed_at = timezone.now()
            task_status.save()
        raise Exception(error_msg)

    except Exception as e:
        error_msg = str(e)
        traceback = tb.format_exc()

        # Update task status
        if task_status:
            task_status.status = 'FAILURE'
            task_status.error = error_msg
            task_status.traceback = traceback
            task_status.completed_at = timezone.now()
            task_status.save()

        # Update document status
        try:
            document = Document.objects.get(id=document_id)
            document.processing_status = 'failed'
            document.metadata['error'] = error_msg
            document.save()
        except:
            pass

        raise


@shared_task(bind=True)
def generate_answers_async(self, rfp_id: str):
    """
    Async task to generate answers for all questions in an RFP

    Args:
        rfp_id: UUID of the RFP

    Returns:
        dict: Generation results
    """
    task_status = None

    try:
        # Get RFP
        rfp = RFP.objects.get(id=rfp_id)

        # Create task status record
        task_status = TaskStatus.objects.create(
            task_id=self.request.id,
            task_type='answer_generation',
            status='STARTED',
            rfp=rfp
        )
        task_status.started_at = timezone.now()
        task_status.save()

        # Update RFP status
        rfp.status = 'processing'
        rfp.save()

        # Get all questions for this RFP
        questions = rfp.questions.all()
        total_questions = questions.count()

        if total_questions == 0:
            raise Exception("No questions found for this RFP")

        task_status.total_steps = total_questions
        task_status.save()

        # Get RAG pipeline
        pipeline = get_rag_pipeline()

        # Generate answers for each question
        answers_created = 0
        answers_cached = 0

        for idx, question in enumerate(questions, 1):
            # Update progress
            task_status.progress = int((idx / total_questions) * 100)
            task_status.current_step = f'Generating answer {idx}/{total_questions}'
            task_status.save()

            # Generate answer
            result = pipeline.generate_answer(
                question=question.question_text,
                question_context=question.context,
                include_confidence=True,
                use_cache=True
            )

            # Check if this answer came from cache
            is_cached = result.get('metadata', {}).get('cached', False)
            if is_cached:
                answers_cached += 1

            # Create or update answer
            answer, created = Answer.objects.get_or_create(
                question=question,
                defaults={
                    'answer_text': result['answer'],
                    'confidence_score': result.get('confidence_score'),
                    'metadata': result.get('metadata', {}),
                    'cached': is_cached
                }
            )

            if created:
                answers_created += 1

            # Add source chunks
            if result.get('source_chunks'):
                from .models import DocumentChunk
                chunk_ids = [chunk['id'] for chunk in result['source_chunks']]
                chunks = DocumentChunk.objects.filter(chromadb_id__in=chunk_ids)
                answer.source_chunks.set(chunks)

        # Mark RFP as complete
        rfp.status = 'completed'
        rfp.save()

        # Update task status
        task_status.status = 'SUCCESS'
        task_status.progress = 100
        task_status.current_step = 'Complete'
        task_status.result = {
            'total_questions': total_questions,
            'answers_created': answers_created,
            'answers_cached': answers_cached
        }
        task_status.completed_at = timezone.now()
        task_status.save()

        return {
            'success': True,
            'rfp_id': str(rfp_id),
            'total_questions': total_questions,
            'answers_created': answers_created,
            'answers_cached': answers_cached
        }

    except RFP.DoesNotExist:
        error_msg = f"RFP {rfp_id} not found"
        if task_status:
            task_status.status = 'FAILURE'
            task_status.error = error_msg
            task_status.completed_at = timezone.now()
            task_status.save()
        raise Exception(error_msg)

    except Exception as e:
        error_msg = str(e)
        traceback = tb.format_exc()

        # Update task status
        if task_status:
            task_status.status = 'FAILURE'
            task_status.error = error_msg
            task_status.traceback = traceback
            task_status.completed_at = timezone.now()
            task_status.save()

        # Update RFP status
        try:
            rfp = RFP.objects.get(id=rfp_id)
            rfp.status = 'failed'
            rfp.save()
        except:
            pass

        raise


@shared_task(bind=True)
def regenerate_answer_async(self, question_id: str):
    """
    Async task to regenerate a single answer

    Args:
        question_id: UUID of the question

    Returns:
        dict: Regeneration results
    """
    try:
        # Get question
        question = Question.objects.get(id=question_id)

        # Get RAG pipeline
        pipeline = get_rag_pipeline()

        # Generate answer (bypass cache)
        result = pipeline.generate_answer(
            question=question.question_text,
            question_context=question.context,
            include_confidence=True,
            use_cache=False  # Always generate fresh for regeneration
        )

        # Update existing answer
        answer = question.answer
        answer.answer_text = result['answer']
        answer.confidence_score = result.get('confidence_score')
        answer.metadata = result.get('metadata', {})
        answer.regenerated_count += 1
        answer.cached = False  # Not cached since we regenerated
        answer.save()

        # Update source chunks
        if result.get('source_chunks'):
            from .models import DocumentChunk
            chunk_ids = [chunk['id'] for chunk in result['source_chunks']]
            chunks = DocumentChunk.objects.filter(chromadb_id__in=chunk_ids)
            answer.source_chunks.set(chunks)

        return {
            'success': True,
            'question_id': str(question_id),
            'answer_id': str(answer.id),
            'regenerated': True
        }

    except Question.DoesNotExist:
        raise Exception(f"Question {question_id} not found")

    except Exception as e:
        raise
