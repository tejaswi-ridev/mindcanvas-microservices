import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

class SearchService {
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

  async performSearch(searchRequest) {
    const response = await this.api.post('/search/', searchRequest);
    return response.data;
  }

  async getSearchHistory(limit = 50) {
    const response = await this.api.get('/search/history', {
      params: { limit }
    });
    return response.data;
  }

  async getSearchDetail(searchId) {
    const response = await this.api.get(`/search/${searchId}`);
    return response.data;
  }

  async deleteSearch(searchId) {
    const response = await this.api.delete(`/search/${searchId}`);
    return response.data;
  }
}

export const searchService = new SearchService();
