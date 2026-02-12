'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { rfpsApi } from '@/lib/api';
import type { RFP } from '@/lib/types';

export default function RFPsPage() {
  const [rfps, setRfps] = useState<RFP[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadRFPs();
  }, []);

  const loadRFPs = async () => {
    try {
      setLoading(true);
      const data = await rfpsApi.list();
      setRfps(data);
      setError(null);
    } catch (err) {
      setError('Failed to load RFPs');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this RFP?')) return;

    try {
      await rfpsApi.delete(id);
      await loadRFPs();
    } catch (err) {
      setError('Failed to delete RFP');
      console.error(err);
    }
  };

  const getStatusBadge = (status: string) => {
    const colors = {
      completed: 'bg-green-100 text-green-800',
      processing: 'bg-yellow-100 text-yellow-800',
      pending: 'bg-gray-100 text-gray-800',
      failed: 'bg-red-100 text-red-800',
    };
    return colors[status as keyof typeof colors] || colors.pending;
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8 flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">RFPs</h1>
          <p className="text-gray-600">Create and manage RFP responses</p>
        </div>
        <Link
          href="/rfps/new"
          className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition font-medium"
        >
          + Create New RFP
        </Link>
      </div>

      {error && (
        <div className="mb-6 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {loading ? (
        <div className="text-center py-12">
          <p className="text-gray-500">Loading RFPs...</p>
        </div>
      ) : rfps.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
          <p className="text-gray-500 mb-4">No RFPs created yet</p>
          <Link
            href="/rfps/new"
            className="text-blue-600 hover:text-blue-800 font-medium"
          >
            Create your first RFP →
          </Link>
        </div>
      ) : (
        <div className="grid gap-6">
          {rfps.map((rfp) => (
            <div
              key={rfp.id}
              className="bg-white p-6 rounded-lg shadow border border-gray-200 hover:shadow-md transition"
            >
              <div className="flex justify-between items-start mb-4">
                <div className="flex-1">
                  <Link
                    href={`/rfps/${rfp.id}`}
                    className="text-xl font-semibold text-gray-900 hover:text-blue-600"
                  >
                    {rfp.name}
                  </Link>
                  {rfp.description && (
                    <p className="text-gray-600 mt-1">{rfp.description}</p>
                  )}
                </div>
                <span className={`px-3 py-1 text-xs font-semibold rounded-full ${getStatusBadge(rfp.status)}`}>
                  {rfp.status}
                </span>
              </div>

              <div className="flex items-center justify-between text-sm text-gray-500">
                <div className="flex gap-4">
                  <span>{rfp.questions?.length || 0} questions</span>
                  <span>•</span>
                  <span>Created {new Date(rfp.uploaded_at).toLocaleDateString()}</span>
                </div>
                <div className="flex gap-3">
                  <Link
                    href={`/rfps/${rfp.id}`}
                    className="text-blue-600 hover:text-blue-800 font-medium"
                  >
                    View Details
                  </Link>
                  <button
                    onClick={() => handleDelete(rfp.id)}
                    className="text-red-600 hover:text-red-800 font-medium"
                  >
                    Delete
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
