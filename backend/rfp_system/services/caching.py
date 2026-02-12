"""
Answer caching service for faster response times on repeated questions
"""
import hashlib


def normalize_question(question_text: str) -> str:
    """
    Normalize question text for consistent hashing.

    Normalization steps:
    1. Convert to lowercase
    2. Strip leading/trailing whitespace
    3. Replace multiple spaces with single space
    4. Remove common punctuation variations

    Args:
        question_text: Raw question text

    Returns:
        Normalized question text
    """
    # Convert to lowercase and strip
    normalized = question_text.lower().strip()

    # Replace multiple spaces with single space
    normalized = ' '.join(normalized.split())

    # Remove trailing question marks (optional - makes "What is X?" match "What is X")
    normalized = normalized.rstrip('?').rstrip()

    return normalized


def generate_question_hash(question_text: str) -> str:
    """
    Generate a SHA256 hash for a question to use as cache key.

    Args:
        question_text: The question text to hash

    Returns:
        64-character hexadecimal hash string

    Example:
        >>> generate_question_hash("What is your pricing?")
        'a3f5b2c1d4e6f7...'
        >>> generate_question_hash("what is your pricing")  # Same hash
        'a3f5b2c1d4e6f7...'
    """
    normalized = normalize_question(question_text)
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


def find_cached_answer(question_hash: str):
    """
    Find a cached answer for a given question hash.

    Args:
        question_hash: The hash of the question to look up

    Returns:
        Answer object if found, None otherwise
    """
    from rfp_system.models import Question, Answer

    # Find all questions with this hash that have answers
    cached_questions = Question.objects.filter(
        question_hash=question_hash,
        answer__isnull=False  # Only questions with answers
    ).select_related('answer').order_by('-answer__generated_at')

    if cached_questions.exists():
        # Return the most recent answer
        return cached_questions.first().answer

    return None


def get_cache_stats():
    """
    Get statistics about cache usage.

    Returns:
        Dictionary with cache statistics
    """
    from rfp_system.models import Answer
    from django.db.models import Count

    total_answers = Answer.objects.count()
    cached_answers = Answer.objects.filter(cached=True).count()

    return {
        'total_answers': total_answers,
        'cached_answers': cached_answers,
        'cache_rate': (cached_answers / total_answers * 100) if total_answers > 0 else 0,
    }
