// TypeScript interfaces for the RFP system

export interface Document {
  id: string;
  filename: string;
  file_type: string;
  file?: string;
  uploaded_at: string;
  processed: boolean;
  processing_status: 'pending' | 'processing' | 'completed' | 'failed';
  chunk_count: number;
  metadata?: Record<string, any>;
}

export interface DocumentChunk {
  id: string;
  chunk_index: number;
  content: string;
  chromadb_id: string;
  chunk_metadata?: Record<string, any>;
  created_at: string;
}

export interface Question {
  id: string;
  rfp: string;
  question_number: number;
  question_text: string;
  context?: string;
  created_at: string;
  answer?: Answer;
}

export interface Answer {
  id: string;
  question: string;
  question_text: string;
  answer_text: string;
  source_chunks: DocumentChunk[];
  confidence_score?: number;
  generated_at: string;
  regenerated_count: number;
  cached: boolean;
  metadata?: Record<string, any>;
}

export interface RFP {
  id: string;
  name: string;
  description?: string;
  uploaded_at: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  questions: Question[];
}

export interface SearchResult {
  query: string;
  results: Array<{
    chunk_id: string;
    content: string;
    similarity: number;
    metadata: Record<string, any>;
  }>;
  count: number;
}

export interface GenerateAnswersResponse {
  success: boolean;
  rfp_id: string;
  generated_count: number;
  total_questions: number;
  errors: Array<{
    question_id: string;
    error: string;
  }>;
}
