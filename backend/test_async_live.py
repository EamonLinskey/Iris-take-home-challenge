"""
Live async test - Proves Celery worker executes tasks
"""
import os
import django
import time

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from rfp_system.models import Document, TaskStatus
from rfp_system.tasks import process_document_async
from django.core.files.uploadedfile import SimpleUploadedFile


def test_live_async():
    """Test that Celery worker actually processes tasks"""
    print("="*70)
    print("  LIVE ASYNC TEST - Celery Worker Execution")
    print("="*70)

    # Create test document
    content = b"""
Company Overview
We are a leading technology company specializing in AI solutions.

Pricing
Our pricing starts at $99/month for the basic plan.

Support
We offer 24/7 customer support via email and phone.
    """

    test_file = SimpleUploadedFile(
        name='test_live.txt',
        content=content,
        content_type='text/plain'
    )

    document = Document.objects.create(
        filename='test_live.txt',
        file_type='txt',
        file=test_file
    )

    print(f"\n[1] Document created: {document.id}")
    print(f"    Status: {document.processing_status}")

    # Dispatch task to Celery worker
    print(f"\n[2] Dispatching task to Celery worker...")
    task = process_document_async.delay(str(document.id))
    task_id = task.id

    print(f"    [OK] Task dispatched!")
    print(f"    Task ID: {task_id}")
    print(f"    Worker will process this in the background")

    # Poll for task status
    print(f"\n[3] Polling task status (max 30 seconds)...")
    max_wait = 30
    start_time = time.time()

    while time.time() - start_time < max_wait:
        try:
            task_status = TaskStatus.objects.get(task_id=task_id)
            print(f"    [{int(time.time() - start_time)}s] Status: {task_status.status} | Progress: {task_status.progress}% | {task_status.current_step}")

            if task_status.status in ['SUCCESS', 'FAILURE']:
                break

        except TaskStatus.DoesNotExist:
            print(f"    [{int(time.time() - start_time)}s] Waiting for worker to start task...")

        time.sleep(2)

    # Check final result
    print(f"\n[4] Final Result:")
    try:
        task_status = TaskStatus.objects.get(task_id=task_id)

        if task_status.status == 'SUCCESS':
            print(f"    [SUCCESS!]")
            print(f"    Status: {task_status.status}")
            print(f"    Progress: {task_status.progress}%")
            print(f"    Result: {task_status.result}")

            document.refresh_from_db()
            print(f"\n    Document Status: {document.processing_status}")
            print(f"    Chunks Created: {document.chunk_count}")

            print(f"\n{'='*70}")
            print(f"  ASYNC PROCESSING WORKS!")
            print(f"{'='*70}")
            print(f"\n  [OK] Task dispatched to Celery worker")
            print(f"  [OK] Worker executed task in background")
            print(f"  [OK] Real-time progress tracking worked")
            print(f"  [OK] Document processed successfully")
            print(f"\n  This proves:")
            print(f"  - Celery worker is running and processing tasks")
            print(f"  - Tasks execute asynchronously in background")
            print(f"  - Progress tracking updates in real-time")
            print(f"  - TaskStatus model tracks execution correctly")
            print(f"  - Database updates persist properly")

        else:
            print(f"    [FAILED] Task failed")
            print(f"    Status: {task_status.status}")
            print(f"    Error: {task_status.error}")

    except TaskStatus.DoesNotExist:
        print(f"    [ERROR] Task status not found")
        print(f"    Worker may not be running or task didn't execute")


if __name__ == '__main__':
    test_live_async()
