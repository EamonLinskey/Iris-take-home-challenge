'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { rfpsApi } from '@/lib/api';

export default function NewRFPPage() {
  const router = useRouter();
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [questions, setQuestions] = useState([{ text: '', context: '' }]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const addQuestion = () => {
    setQuestions([...questions, { text: '', context: '' }]);
  };

  const removeQuestion = (index: number) => {
    setQuestions(questions.filter((_, i) => i !== index));
  };

  const updateQuestion = (index: number, field: 'text' | 'context', value: string) => {
    const updated = [...questions];
    updated[index][field] = value;
    setQuestions(updated);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // Validation
    if (!name.trim()) {
      setError('Please enter an RFP name');
      return;
    }

    const validQuestions = questions.filter(q => q.text.trim());
    if (validQuestions.length === 0) {
      setError('Please add at least one question');
      return;
    }

    try {
      setSubmitting(true);
      const rfp = await rfpsApi.create({
        name: name.trim(),
        description: description.trim() || undefined,
        questions: validQuestions.map(q => ({
          question_text: q.text.trim(),
          context: q.context.trim() || undefined,
        })),
      });

      // Redirect to the RFP detail page
      router.push(`/rfps/${rfp.id}`);
    } catch (err) {
      setError('Failed to create RFP. Please try again.');
      console.error(err);
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <Link href="/rfps" className="text-blue-600 hover:text-blue-800 mb-4 inline-block">
          ← Back to RFPs
        </Link>
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Create New RFP</h1>
        <p className="text-gray-600">
          Add questions and the AI will generate answers using your knowledge base
        </p>
      </div>

      {error && (
        <div className="mb-6 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="bg-white p-6 rounded-lg shadow border border-gray-200">
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              RFP Name *
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="e.g., Q1 2024 Enterprise Software RFP"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Description (Optional)
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              rows={3}
              placeholder="Brief description of this RFP..."
            />
          </div>
        </div>

        <div>
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold text-gray-900">Questions</h2>
            <button
              type="button"
              onClick={addQuestion}
              className="text-blue-600 hover:text-blue-800 font-medium"
            >
              + Add Question
            </button>
          </div>

          <div className="space-y-4">
            {questions.map((question, index) => (
              <div key={index} className="bg-white p-6 rounded-lg shadow border border-gray-200">
                <div className="flex justify-between items-start mb-4">
                  <h3 className="font-medium text-gray-900">Question {index + 1}</h3>
                  {questions.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeQuestion(index)}
                      className="text-red-600 hover:text-red-800 text-sm"
                    >
                      Remove
                    </button>
                  )}
                </div>

                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Question Text *
                    </label>
                    <textarea
                      value={question.text}
                      onChange={(e) => updateQuestion(index, 'text', e.target.value)}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      rows={3}
                      placeholder="e.g., What is your company's experience with enterprise software?"
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Additional Context (Optional)
                    </label>
                    <input
                      type="text"
                      value={question.context}
                      onChange={(e) => updateQuestion(index, 'context', e.target.value)}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      placeholder="Any additional context for this question..."
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="flex gap-4">
          <button
            type="submit"
            disabled={submitting}
            className="flex-1 bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition"
          >
            {submitting ? 'Creating...' : 'Create RFP'}
          </button>
          <Link
            href="/rfps"
            className="px-6 py-3 rounded-lg border border-gray-300 hover:bg-gray-50 font-medium transition text-center"
          >
            Cancel
          </Link>
        </div>
      </form>
    </div>
  );
}
