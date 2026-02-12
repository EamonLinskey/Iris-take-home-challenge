// API client for communicating with Django backend

import axios from 'axios';
import type { Document, RFP, SearchResult, GenerateAnswersResponse } from './types';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Documents API
export const documentsApi = {
  // List all documents
  list: async () => {
    const response = await api.get<{ results: Document[] }>('/documents/');
    return response.data.results;
  },

  // Get single document
  get: async (id: string) => {
    const response = await api.get<Document>(`/documents/${id}/`);
    return response.data;
  },

  // Upload document
  upload: async (file: File, filename?: string, fileType?: string) => {
    const formData = new FormData();
    formData.append('file', file);
    if (filename) formData.append('filename', filename);
    if (fileType) formData.append('file_type', fileType);

    const response = await api.post<Document>('/documents/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // Delete document
  delete: async (id: string) => {
    await api.delete(`/documents/${id}/`);
  },
};

// RFPs API
export const rfpsApi = {
  // List all RFPs
  list: async () => {
    const response = await api.get<{ results: RFP[] }>('/rfps/');
    return response.data.results;
  },

  // Get single RFP with questions and answers
  get: async (id: string) => {
    const response = await api.get<RFP>(`/rfps/${id}/`);
    return response.data;
  },

  // Create new RFP
  create: async (data: {
    name: string;
    description?: string;
    questions: Array<{ question_text: string; context?: string }>;
  }) => {
    const response = await api.post<RFP>('/rfps/', data);
    return response.data;
  },

  // Generate answers for all questions in an RFP
  generateAnswers: async (id: string, includeConfidence: boolean = true, topK: number = 5) => {
    const response = await api.post<GenerateAnswersResponse>(
      `/rfps/${id}/generate_answers/`,
      {
        include_confidence: includeConfidence,
        top_k: topK,
      }
    );
    return response.data;
  },

  // Delete RFP
  delete: async (id: string) => {
    await api.delete(`/rfps/${id}/`);
  },
};

// Questions API
export const questionsApi = {
  // Regenerate answer for a specific question
  regenerate: async (id: string, includeConfidence: boolean = true, topK: number = 5) => {
    const response = await api.post(`/questions/${id}/regenerate/`, {
      include_confidence: includeConfidence,
      top_k: topK,
    });
    return response.data;
  },
};

// Search API
export const searchApi = {
  // Perform semantic search
  search: async (query: string, topK: number = 5, similarityThreshold: number = 0.3) => {
    const response = await api.post<SearchResult>('/search/', {
      query,
      top_k: topK,
      similarity_threshold: similarityThreshold,
    });
    return response.data;
  },
};

export default api;
