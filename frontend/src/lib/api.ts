import axios from 'axios';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api/v1';

export const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface HealthResponse {
  status: 'ok';
  service: string;
  version: string;
  environment: string;
}

export interface UploadResponse {
  document_id: string;
  filename: string;
  content_type: string | null;
  status: string;
}

export interface OcrBlock {
  text: string;
  confidence: number;
  bbox: number[];
  page: number;
  orientation: 'horizontal' | 'vertical' | 'unknown';
}

export interface OcrResult {
  document_id: string;
  text: string;
  blocks: OcrBlock[];
  confidence: number;
  status: string;
}

export interface ExtractionResult {
  document_id: string;
  data: Record<string, unknown>;
  confidence: number;
  status: string;
}

export interface ValidationIssue {
  field: string;
  message: string;
  severity: 'info' | 'warning' | 'error';
}

export interface ValidationResult {
  document_id: string;
  valid: boolean;
  confidence: number;
  issues: ValidationIssue[];
  status: string;
}

export interface PipelineRunResponse {
  document_id: string;
  ocr: OcrResult;
  extraction: ExtractionResult;
  validation: ValidationResult;
}

export interface FeedbackRequest {
  document_id: string;
  corrections: Record<string, unknown>;
  user?: string;
  notes?: string;
}

export interface FeedbackResponse {
  document_id: string;
  stored: boolean;
  status: string;
}

export interface StoredDocument {
  document_id: string;
  document_type: string | null;
  data: Record<string, unknown>;
  summary: string | null;
  saved_at: string | null;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface ChatResponse {
  document_id: string;
  reply: string;
}

export const apiService = {
  getDocumentFileUrl(documentId: string): string {
    return `${BASE_URL}/documents/${documentId}/file`;
  },

  /**
   * Get system health status
   */
  async getHealth(): Promise<HealthResponse> {
    const response = await apiClient.get<HealthResponse>('/healthz');
    return response.data;
  },

  /**
   * Upload a new document file (PDF or Image)
   */
  async uploadDocument(file: File): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    const response = await apiClient.post<UploadResponse>('/documents', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  /**
   * Run the full pipeline baseline (OCR -> Extraction -> Validation)
   */
  async runPipeline(documentId: string, documentType: string = 'unknown'): Promise<PipelineRunResponse> {
    const response = await apiClient.post<PipelineRunResponse>('/pipeline/run', {
      document_id: documentId,
      document_type: documentType,
    });
    return response.data;
  },

  /**
   * Submit human corrections and notes (feedback loop)
   */
  async submitFeedback(feedback: FeedbackRequest): Promise<FeedbackResponse> {
    const response = await apiClient.post<FeedbackResponse>('/feedback', feedback);
    return response.data;
  },

  /**
   * List documents that have been extracted and stored for the chatbot
   */
  async listExtractedDocuments(): Promise<StoredDocument[]> {
    const response = await apiClient.get<StoredDocument[]>('/documents/extracted');
    return response.data;
  },

  /**
   * Ask the Qwen2.5 chatbot a question about a specific extracted document
   */
  async chatWithDocument(
    documentId: string,
    message: string,
    history: ChatMessage[] = []
  ): Promise<ChatResponse> {
    const response = await apiClient.post<ChatResponse>('/chat', {
      document_id: documentId,
      message,
      history,
    });
    return response.data;
  },
};
