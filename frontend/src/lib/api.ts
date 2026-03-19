import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

// 作词人相关 API
export const lyricistApi = {
  list: (params?: { skip?: number; limit?: number; search?: string }) =>
    api.get('/lyricists', { params }),
  
  get: (id: number) =>
    api.get(`/lyricists/${id}`),
  
  create: (data: { name: string; alias?: string; style?: string; description?: string }) =>
    api.post('/lyricists', data),
  
  update: (id: number, data: { name?: string; alias?: string; style?: string; description?: string }) =>
    api.put(`/lyricists/${id}`, data),
  
  delete: (id: number) =>
    api.delete(`/lyricists/${id}`),
}

// 歌词样本相关 API
export const sampleApi = {
  list: (params?: { skip?: number; limit?: number; lyricist_id?: number; status?: string; search?: string }) =>
    api.get('/samples', { params }),
  
  get: (id: number) =>
    api.get(`/samples/${id}`),
  
  create: (data: { lyricist_id: number; title?: string; content: string; source?: string; tags?: string[] }) =>
    api.post('/samples', data),
  
  update: (id: number, data: { title?: string; content?: string; source?: string; tags?: string[]; status?: string }) =>
    api.put(`/samples/${id}`, data),
  
  delete: (id: number) =>
    api.delete(`/samples/${id}`),
  
  batchCreate: (samples: Array<{ lyricist_id: number; title?: string; content: string; source?: string; tags?: string[] }>) =>
    api.post('/samples/batch', samples),
}

// 模型相关 API
export const modelApi = {
  list: (params?: { skip?: number; limit?: number; lyricist_id?: number; status?: string }) =>
    api.get('/models', { params }),
  
  get: (id: number) =>
    api.get(`/models/${id}`),
  
  create: (data: { lyricist_id: number; name: string; version?: string; base_model?: string; config?: any }) =>
    api.post('/models', data),
  
  getStatus: (id: number) =>
    api.get(`/models/${id}/status`),
  
  stop: (id: number) =>
    api.post(`/models/${id}/stop`),
  
  delete: (id: number) =>
    api.delete(`/models/${id}`),
}

// 生成相关 API
export const generationApi = {
  generate: (data: { model_id: number; input_text?: string; mode?: string; config?: any }) =>
    api.post('/generation/generate', data),
  
  history: (params?: { skip?: number; limit?: number; model_id?: number }) =>
    api.get('/generation/history', { params }),
  
  save: (id: number) =>
    api.post(`/generation/${id}/save`),
  
  rate: (id: number, rating: number) =>
    api.post(`/generation/${id}/rate`, null, { params: { rating } }),
}

export default api
