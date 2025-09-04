import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

class DashboardService {
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

  async getSearchHistory(limit = 10) {
    const response = await this.api.get('/dashboard/search', {
      params: { limit }
    });
    return response.data;
  }

  async getImageHistory(limit = 10) {
    const response = await this.api.get('/dashboard/images', {
      params: { limit }
    });
    return response.data;
  }

  async getUserStats() {
    const response = await this.api.get('/dashboard/stats');
    return response.data;
  }

  async deleteSearch(searchId) {
    const response = await this.api.delete(`/dashboard/search/${searchId}`);
    return response.data;
  }

  async deleteImage(imageId) {
    const response = await this.api.delete(`/dashboard/image/${imageId}`);
    return response.data;
  }

  async exportCSV() {
    const response = await this.api.get('/dashboard/export/csv', {
      responseType: 'blob'
    });

    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', 'mindcanvas_data.csv');
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);

    return response.data;
  }

  async exportPDF() {
    const response = await this.api.get('/dashboard/export/pdf', {
      responseType: 'blob'
    });

    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', 'mindcanvas_data.pdf');
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);

    return response.data;
  }
}

export const dashboardService = new DashboardService();
