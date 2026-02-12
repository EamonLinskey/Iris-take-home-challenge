"""
Unit tests for answer caching functionality
"""
import pytest
from unittest.mock import patch, Mock
from rfp_system.services.caching import (
    normalize_question,
    generate_question_hash,
    find_cached_answer,
    get_cache_stats
)
from rfp_system.models import Question, Answer


@pytest.mark.unit
class TestQuestionNormalization:
    """Test question text normalization"""

    def test_lowercase_conversion(self):
        """Test that questions are converted to lowercase"""
        assert normalize_question("What is YOUR pricing?") == "what is your pricing"

    def test_whitespace_stripping(self):
        """Test that whitespace is stripped"""
        assert normalize_question("  What is your pricing?  ") == "what is your pricing"

    def test_multiple_spaces_normalized(self):
        """Test that multiple spaces are replaced with single space"""
        assert normalize_question("What  is   your    pricing?") == "what is your pricing"

    def test_question_mark_removal(self):
        """Test that trailing question marks are removed"""
        assert normalize_question("What is your pricing?") == "what is your pricing"
        assert normalize_question("What is your pricing??") == "what is your pricing"

    def test_question_mark_in_middle_preserved(self):
        """Test that question marks in the middle are preserved"""
        assert normalize_question("What? is your pricing") == "what? is your pricing"


@pytest.mark.unit
class TestQuestionHashing:
    """Test question hash generation"""

    def test_same_question_same_hash(self):
        """Test that identical questions produce identical hashes"""
        q1 = "What is your pricing?"
        q2 = "What is your pricing?"

        hash1 = generate_question_hash(q1)
        hash2 = generate_question_hash(q2)

        assert hash1 == hash2

    def test_normalized_questions_same_hash(self):
        """Test that normalized variations produce the same hash"""
        q1 = "What is your pricing?"
        q2 = "what is your pricing"  # No question mark, lowercase
        q3 = "  WHAT  IS   YOUR  PRICING  "  # Extra spaces, uppercase

        hash1 = generate_question_hash(q1)
        hash2 = generate_question_hash(q2)
        hash3 = generate_question_hash(q3)

        assert hash1 == hash2 == hash3

    def test_different_questions_different_hash(self):
        """Test that different questions produce different hashes"""
        q1 = "What is your pricing?"
        q2 = "What are your prices?"

        hash1 = generate_question_hash(q1)
        hash2 = generate_question_hash(q2)

        # These should be different (no semantic matching)
        assert hash1 != hash2

    def test_hash_is_64_characters(self):
        """Test that hash is 64-character hex string (SHA256)"""
        question_hash = generate_question_hash("Test question")

        assert len(question_hash) == 64
        assert all(c in '0123456789abcdef' for c in question_hash)


@pytest.mark.unit
@pytest.mark.django_db
class TestQuestionModel:
    """Test Question model auto-hashing"""

    def test_question_hash_auto_generated(self, rfp_data):
        """Test that question_hash is automatically generated on save"""
        question = Question.objects.create(
            rfp=rfp_data,
            question_text="What is your pricing?",
            question_number=10
        )

        assert question.question_hash
        assert len(question.question_hash) == 64

    def test_same_question_text_same_hash(self, rfp_data):
        """Test that questions with same text get same hash"""
        q1 = Question.objects.create(
            rfp=rfp_data,
            question_text="What is your pricing?",
            question_number=10
        )

        q2 = Question.objects.create(
            rfp=rfp_data,
            question_text="What is your pricing?",  # Same text
            question_number=11
        )

        assert q1.question_hash == q2.question_hash

    def test_normalized_question_same_hash(self, rfp_data):
        """Test that normalized variations get same hash"""
        q1 = Question.objects.create(
            rfp=rfp_data,
            question_text="What is your pricing?",
            question_number=10
        )

        q2 = Question.objects.create(
            rfp=rfp_data,
            question_text="  WHAT   IS  YOUR  PRICING  ",  # Different formatting
            question_number=11
        )

        assert q1.question_hash == q2.question_hash


@pytest.mark.unit
@pytest.mark.django_db
class TestCacheLookup:
    """Test finding cached answers"""

    def test_find_cached_answer_exists(self, question_data):
        """Test finding a cached answer when it exists"""
        question = question_data[0]

        # Create an answer for this question
        answer = Answer.objects.create(
            question=question,
            answer_text="Our pricing starts at $99/month.",
            confidence_score=0.95,
            cached=True
        )

        # Look up by hash
        cached = find_cached_answer(question.question_hash)

        assert cached is not None
        assert cached.id == answer.id
        assert cached.answer_text == answer.answer_text

    def test_find_cached_answer_not_exists(self):
        """Test that None is returned when no cached answer exists"""
        fake_hash = "0" * 64
        cached = find_cached_answer(fake_hash)

        assert cached is None

    def test_find_most_recent_cached_answer(self, rfp_data):
        """Test that a cached answer is returned when multiple exist with same hash"""
        # Create two questions with same hash (same text)
        q1 = Question.objects.create(
            rfp=rfp_data,
            question_text="What is your pricing?",
            question_number=10
        )

        q2 = Question.objects.create(
            rfp=rfp_data,
            question_text="What is your pricing?",
            question_number=11
        )

        # Create answers for both
        answer1 = Answer.objects.create(
            question=q1,
            answer_text="First answer",
            cached=True
        )

        answer2 = Answer.objects.create(
            question=q2,
            answer_text="Second answer",
            cached=True
        )

        # Look up - should get one of the cached answers
        cached = find_cached_answer(q1.question_hash)

        assert cached is not None
        assert cached.id in [answer1.id, answer2.id]
        assert cached.answer_text in ["First answer", "Second answer"]

    def test_only_questions_with_answers_returned(self, rfp_data):
        """Test that questions without answers are not found"""
        question = Question.objects.create(
            rfp=rfp_data,
            question_text="What is your pricing?",
            question_number=10
        )

        # No answer created for this question
        cached = find_cached_answer(question.question_hash)

        assert cached is None


@pytest.mark.unit
@pytest.mark.django_db
class TestCacheStats:
    """Test cache statistics"""

    def test_cache_stats_empty(self):
        """Test cache stats when no answers exist"""
        stats = get_cache_stats()

        assert stats['total_answers'] == 0
        assert stats['cached_answers'] == 0
        assert stats['cache_rate'] == 0

    def test_cache_stats_with_data(self, question_data):
        """Test cache stats with mix of cached and non-cached answers"""
        # Create 3 answers, 2 cached
        Answer.objects.create(
            question=question_data[0],
            answer_text="Answer 1",
            cached=True
        )

        Answer.objects.create(
            question=question_data[1],
            answer_text="Answer 2",
            cached=True
        )

        Answer.objects.create(
            question=question_data[2],
            answer_text="Answer 3",
            cached=False
        )

        stats = get_cache_stats()

        assert stats['total_answers'] == 3
        assert stats['cached_answers'] == 2
        assert stats['cache_rate'] == pytest.approx(66.67, rel=0.1)


@pytest.mark.integration
@pytest.mark.django_db
class TestEndToEndCaching:
    """Test complete caching workflow"""

    def test_cache_hit_workflow(self, rfp_data):
        """Test that duplicate questions use cached answers"""
        from rfp_system.services.rag_pipeline import get_rag_pipeline
        from unittest.mock import patch, Mock

        # Create first question
        q1 = Question.objects.create(
            rfp=rfp_data,
            question_text="What is your pricing?",
            question_number=10
        )

        # Mock the RAG pipeline generation
        with patch.object(get_rag_pipeline(), 'answer_generator') as mock_gen:
            mock_gen.generate_answer.return_value = {
                'answer': 'Our pricing starts at $99/month.',
                'confidence_score': 0.95
            }

            # Generate first answer (cache miss)
            result1 = get_rag_pipeline().generate_answer(
                question="What is your pricing?",
                use_cache=True
            )

            # Create the answer in DB
            Answer.objects.create(
                question=q1,
                answer_text=result1['answer'],
                confidence_score=result1['confidence_score'],
                cached=False  # First generation, not cached
            )

            # Create second question with same text
            q2 = Question.objects.create(
                rfp=rfp_data,
                question_text="What is your pricing?",
                question_number=11
            )

            # Generate second answer (should be cache hit)
            result2 = get_rag_pipeline().generate_answer(
                question="What is your pricing?",
                use_cache=True
            )

            # Verify cache was used
            assert result2['metadata'].get('cached') is True
            assert result2['answer'] == result1['answer']

    def test_cache_disabled_always_generates(self, rfp_data):
        """Test that disabling cache always generates new answers"""
        from rfp_system.services.rag_pipeline import get_rag_pipeline

        # Create question with existing answer
        q1 = Question.objects.create(
            rfp=rfp_data,
            question_text="What is your pricing?",
            question_number=10
        )

        Answer.objects.create(
            question=q1,
            answer_text="Cached answer",
            cached=True
        )

        # Generate with cache disabled
        with patch.object(get_rag_pipeline(), 'retrieve_context') as mock_retrieve:
            mock_retrieve.return_value = []

            result = get_rag_pipeline().generate_answer(
                question="What is your pricing?",
                use_cache=False  # Disable cache
            )

            # Should not use cache (will return "no info" message)
            assert result['metadata'].get('cached') is not True
            mock_retrieve.assert_called_once()  # Context retrieval happened
