export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  token: string;
  username: string;
}

export interface FileInfo {
  name: string;
  size: string;
  modified: string;
}

export interface FileContent {
  content: string;
  metadata: {
    filename: string;
    size_bytes: number;
    line_count: number;
    last_modified: string;
    mime_type: string;
  };
}

export interface HealthStatus {
  status: string;
  ai_available: boolean;
  connected_clients: number;
  files_count: number;
}

export interface SearchResponse {
  query: string;
  matches: string[];
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  isStreaming?: boolean;
}

export interface FileSummary {
  executive_summary: string;
  key_topics: string[];
  sentiment: 'positive' | 'neutral' | 'negative';
  follow_up_questions: string[];
}
