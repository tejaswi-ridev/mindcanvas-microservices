import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

class ImageService {
  constructor() {
    this.api = axios.create({
      baseURL: API_BASE_URL,
    });

    this.api.interceptors.request.use((config) => {
      const token = localStorage.getItem('token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });
  }

  async generateImage(imageRequest) {
    const response = await this.api.post('/image/generate', imageRequest);
    return response.data;
  }

  async getImageHistory(limit = 50) {
    const response = await this.api.get('/image/history', {
      params: { limit }
    });
    return response.data;
  }

  async getImageDetail(imageId) {
    const response = await this.api.get(`/image/${imageId}`);
    return response.data;
  }

  async deleteImage(imageId) {
    const response = await this.api.delete(`/image/${imageId}`);
    return response.data;
  }
}

export const imageService = new ImageService();
