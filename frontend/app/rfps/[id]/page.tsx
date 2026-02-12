'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { rfpsApi, questionsApi } from '@/lib/api';
import type { RFP, Answer } from '@/lib/types';

export default function RFPDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const [rfp, setRfp] = useState<RFP | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [regeneratingId, setRegeneratingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [resolvedParams, setResolvedParams] = useState<{id: string} | null>(null);

  useEffect(() => {
    params.then(p => {
      setResolvedParams(p);
      loadRFP(p.id);
    });
  }, [params]);

  const loadRFP = async (id: string) => {
    try {
      setLoading(true);
      const data = await rfpsApi.get(id);
      setRfp(data);
      setError(null);
    } catch (err) {
      setError('Failed to load RFP');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateAnswers = async () => {
    if (!resolvedParams) return;

    try {
      setGenerating(true);
      setError(null);
      await rfpsApi.generateAnswers(resolvedParams.id);
      await loadRFP(resolvedParams.id);
    } catch (err) {
      setError('Failed to generate answers');
      console.error(err);
    } finally {
      setGenerating(false);
    }
  };

  const handleRegenerateAnswer = async (questionId: string) => {
    if (!resolvedParams) return;

    try {
      setRegeneratingId(questionId);
      setError(null);
      await questionsApi.regenerate(questionId);
      await loadRFP(resolvedParams.id);
    } catch (err) {
      setError('Failed to regenerate answer');
      console.error(err);
    } finally {
      setRegeneratingId(null);
    }
  };

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="text-center py-12">
          <p className="text-gray-500">Loading RFP...</p>
        </div>
      </div>
    );
  }

  if (!rfp) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="text-center py-12">
          <p className="text-red-600">RFP not found</p>
        </div>
      </div>
    );
  }

  const hasAnswers = rfp.questions.some(q => q.answer);
  const allAnswered = rfp.questions.every(q => q.answer);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <Link href="/rfps" className="text-blue-600 hover:text-blue-800 mb-4 inline-block">
          ← Back to RFPs
        </Link>
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">{rfp.name}</h1>
            {rfp.description && <p className="text-gray-600">{rfp.description}</p>}
            <p className="text-sm text-gray-500 mt-2">
              Created {new Date(rfp.uploaded_at).toLocaleDateString()}
            </p>
          </div>
          {!allAnswered && (
            <button
              onClick={handleGenerateAnswers}
              disabled={generating}
              className="bg-green-600 text-white px-6 py-3 rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition"
            >
              {generating ? 'Generating...' : hasAnswers ? 'Generate Missing Answers' : 'Generate All Answers'}
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="mb-6 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      <div className="space-y-8">
        {rfp.questions.map((question, index) => (
          <div key={question.id} className="bg-white rounded-lg shadow border border-gray-200 overflow-hidden">
            <div className="bg-gray-50 px-6 py-4 border-b border-gray-200">
              <div className="flex justify-between items-start">
                <h2 className="text-lg font-semibold text-gray-900">
                  Question {index + 1}
                </h2>
                {question.answer && (
                  <button
                    onClick={() => handleRegenerateAnswer(question.id)}
                    disabled={regeneratingId === question.id}
                    className="text-sm text-blue-600 hover:text-blue-800 disabled:opacity-50"
                  >
                    {regeneratingId === question.id ? 'Regenerating...' : '↻ Regenerate'}
                  </button>
                )}
              </div>
              <p className="text-gray-700 mt-2 whitespace-pre-wrap">{question.question_text}</p>
              {question.context && (
                <p className="text-sm text-gray-500 mt-2">Context: {question.context}</p>
              )}
            </div>

            <div className="px-6 py-6">
              {question.answer ? (
                <AnswerDisplay answer={question.answer} />
              ) : (
                <p className="text-gray-500 italic">No answer generated yet</p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function AnswerDisplay({ answer }: { answer: Answer }) {
  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center gap-3 mb-3">
          <h3 className="font-semibold text-gray-900">Answer</h3>
          {answer.confidence_score !== undefined && answer.confidence_score !== null && (
            <span className="px-2 py-1 bg-blue-100 text-blue-800 text-xs font-semibold rounded">
              {Math.round(answer.confidence_score * 100)}% confidence
            </span>
          )}
        </div>
        <div className="prose max-w-none text-gray-700 whitespace-pre-wrap">
          {answer.answer_text}
        </div>
      </div>

      {answer.source_chunks && answer.source_chunks.length > 0 && (
        <div>
          <h3 className="font-semibold text-gray-900 mb-3">
            Source Documents ({answer.source_chunks.length})
          </h3>
          <div className="space-y-3">
            {answer.source_chunks.map((chunk, idx) => (
              <div key={chunk.id} className="bg-gray-50 p-4 rounded border border-gray-200">
                <div className="text-xs text-gray-500 mb-2">
                  Source {idx + 1}: {chunk.chunk_metadata?.filename || 'Unknown'}
                </div>
                <div className="text-sm text-gray-700 line-clamp-3">
                  {chunk.content}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="text-xs text-gray-500 pt-4 border-t border-gray-200">
        Generated {new Date(answer.generated_at).toLocaleString()}
        {answer.regenerated_count > 0 && ` • Regenerated ${answer.regenerated_count} time(s)`}
      </div>
    </div>
  );
}
