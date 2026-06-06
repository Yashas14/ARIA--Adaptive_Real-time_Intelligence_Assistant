import axios from 'axios';
import type { LoginRequest, LoginResponse, FileInfo, FileContent, SearchResponse, HealthStatus } from '../types';

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
});

// Attach JWT token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Redirect to login on 401
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('username');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const authApi = {
  login: async (data: LoginRequest): Promise<LoginResponse> => {
    const res = await api.post<LoginResponse>('/auth/login', data);
    return res.data;
  },
};

export const filesApi = {
  list: async (): Promise<FileInfo[]> => {
    const res = await api.get<FileInfo[]>('/files');
    return res.data;
  },

  get: async (filename: string): Promise<FileContent> => {
    const res = await api.get<FileContent>(`/files/${encodeURIComponent(filename)}`);
    return res.data;
  },

  summarize: (filename: string, onToken: (token: string) => void, onDone: () => void) => {
    const token = localStorage.getItem('token');
    const controller = new AbortController();

    fetch(`/api/files/${encodeURIComponent(filename)}/summarize`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      signal: controller.signal,
    }).then(async (response) => {
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      if (!reader) return;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const text = decoder.decode(value, { stream: true });
        const lines = text.split('\n');
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data) onToken(data);
          }
          if (line.startsWith('event: done')) {
            onDone();
          }
        }
      }
      onDone();
    });

    return () => controller.abort();
  },

  search: async (query: string): Promise<SearchResponse> => {
    const res = await api.post<SearchResponse>('/search', { query });
    return res.data;
  },
};

export const chatApi = {
  stream: (message: string, onToken: (token: string) => void, onDone: () => void) => {
    const token = localStorage.getItem('token');
    const controller = new AbortController();

    fetch('/api/chat', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ message }),
      signal: controller.signal,
    }).then(async (response) => {
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      if (!reader) return;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const text = decoder.decode(value, { stream: true });
        const lines = text.split('\n');
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data) onToken(data);
          }
          if (line.startsWith('event: done')) {
            onDone();
          }
        }
      }
      onDone();
    }).catch(() => {
      onDone();
    });

    return () => controller.abort();
  },

  getHistory: async () => {
    const res = await api.get('/history');
    return res.data;
  },

  clearHistory: async () => {
    await api.delete('/history');
  },
};

export const healthApi = {
  check: async (): Promise<HealthStatus> => {
    const res = await api.get<HealthStatus>('/health');
    return res.data;
  },
};

export default api;
