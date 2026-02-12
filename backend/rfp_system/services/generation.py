"""
Answer generation service using Claude API
"""
from typing import List, Dict, Optional
import anthropic
from django.conf import settings


class AnswerGenerator:
    """Generate answers to RFP questions using Claude with RAG context"""

    def __init__(self):
        """Initialize Claude API client"""
        api_key = getattr(settings, 'ANTHROPIC_API_KEY', None)
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in settings")

        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "claude-3-5-sonnet-20241022"
        self.max_tokens = 2000
        self.temperature = 0.3  # Low for consistency in professional responses

    def generate_answer(
        self,
        question: str,
        context_chunks: List[str],
        question_context: str = None,
        include_confidence: bool = False
    ) -> Dict:
        """
        Generate an answer to an RFP question using retrieved context

        Args:
            question: The RFP question to answer
            context_chunks: List of relevant document chunks for context
            question_context: Optional additional context about the question
            include_confidence: Whether to ask Claude for a confidence score

        Returns:
            Dictionary with 'answer', 'metadata', and optionally 'confidence_score'
        """
        # Build the prompt
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(
            question=question,
            context_chunks=context_chunks,
            question_context=question_context,
            include_confidence=include_confidence
        )

        try:
            # Call Claude API
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )

            # Extract answer from response
            answer_text = response.content[0].text

            # Parse confidence score if requested
            confidence_score = None
            if include_confidence:
                confidence_score = self._parse_confidence(answer_text)
                # Remove confidence marker from answer if present
                answer_text = self._remove_confidence_marker(answer_text)

            # Build metadata
            metadata = {
                'model': self.model,
                'input_tokens': response.usage.input_tokens,
                'output_tokens': response.usage.output_tokens,
                'stop_reason': response.stop_reason,
                'context_chunks_count': len(context_chunks)
            }

            return {
                'answer': answer_text.strip(),
                'confidence_score': confidence_score,
                'metadata': metadata
            }

        except Exception as e:
            print(f"Error generating answer with Claude: {str(e)}")
            raise

    def _build_system_prompt(self) -> str:
        """Build the system prompt for Claude"""
        return """You are an expert RFP response writer. Your role is to generate professional, accurate answers to RFP questions based on company knowledge base documents.

Guidelines:
- Use ONLY information from the provided context chunks
- Write in a professional, confident tone appropriate for RFP responses
- Be specific and detailed - include relevant facts, numbers, and examples from the context
- If the context doesn't contain enough information to fully answer the question, acknowledge this and answer with what you can
- Structure longer answers with clear paragraphs or bullet points
- Do not make up information - only use what's in the provided context
- Avoid phrases like "based on the documents" or "according to the context" - write as if this is your company's knowledge"""

    def _build_user_prompt(
        self,
        question: str,
        context_chunks: List[str],
        question_context: str = None,
        include_confidence: bool = False
    ) -> str:
        """Build the user prompt with question and context"""

        # Format context chunks
        context_section = "CONTEXT FROM COMPANY DOCUMENTS:\n\n"
        for idx, chunk in enumerate(context_chunks, 1):
            context_section += f"[Document Chunk {idx}]\n{chunk}\n\n"

        # Build question section
        question_section = f"RFP QUESTION:\n{question}"

        if question_context:
            question_section += f"\n\nAdditional Context: {question_context}"

        # Confidence instruction
        confidence_section = ""
        if include_confidence:
            confidence_section = "\n\nAfter your answer, on a new line, provide your confidence score as: CONFIDENCE: [0.0-1.0]"

        prompt = f"""{context_section}

{question_section}

Please provide a professional, detailed answer to this RFP question using the context above.{confidence_section}"""

        return prompt

    def _parse_confidence(self, answer_text: str) -> Optional[float]:
        """Extract confidence score from answer if present"""
        import re

        # Look for pattern like "CONFIDENCE: 0.85"
        match = re.search(r'CONFIDENCE:\s*([0-9]*\.?[0-9]+)', answer_text, re.IGNORECASE)
        if match:
            try:
                score = float(match.group(1))
                return min(max(score, 0.0), 1.0)  # Clamp between 0 and 1
            except ValueError:
                pass
        return None

    def _remove_confidence_marker(self, answer_text: str) -> str:
        """Remove confidence score line from answer"""
        import re
        return re.sub(r'\n*CONFIDENCE:\s*[0-9]*\.?[0-9]+\s*$', '', answer_text, flags=re.IGNORECASE)

    def batch_generate_answers(
        self,
        questions: List[Dict],
        context_retriever,
        include_confidence: bool = False
    ) -> List[Dict]:
        """
        Generate answers for multiple questions

        Args:
            questions: List of question dictionaries with 'text' and optionally 'context'
            context_retriever: Function that takes question text and returns context chunks
            include_confidence: Whether to include confidence scores

        Returns:
            List of answer dictionaries
        """
        answers = []

        for question_data in questions:
            question_text = question_data.get('text', '')
            question_context = question_data.get('context', None)

            # Retrieve context chunks for this question
            context_chunks = context_retriever(question_text)

            # Generate answer
            try:
                result = self.generate_answer(
                    question=question_text,
                    context_chunks=context_chunks,
                    question_context=question_context,
                    include_confidence=include_confidence
                )
                answers.append(result)
            except Exception as e:
                # Return error result for this question
                answers.append({
                    'answer': f"Error generating answer: {str(e)}",
                    'confidence_score': 0.0,
                    'metadata': {'error': str(e)}
                })

        return answers


# Singleton instance
_generator = None

def get_answer_generator() -> AnswerGenerator:
    """Get singleton instance of answer generator"""
    global _generator
    if _generator is None:
        _generator = AnswerGenerator()
    return _generator
