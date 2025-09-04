import React, { useState, useEffect } from 'react';
// CORRECTED: Import the Link component for SPA navigation
import { Link } from 'react-router-dom';
import { dashboardService } from '../services/dashboardService';

function DashboardPage() {
  const [searchHistory, setSearchHistory] = useState([]);
  const [imageHistory, setImageHistory] = useState([]);
  const [stats, setStats] = useState({ total_searches: 0, total_images: 0 });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      const [searches, images, userStats] = await Promise.all([
        dashboardService.getSearchHistory(10),
        dashboardService.getImageHistory(10),
        dashboardService.getUserStats()
      ]);

      setSearchHistory(searches);
      setImageHistory(images);
      setStats(userStats);
    } catch (error) {
      console.error('Error loading dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteSearch = async (searchId) => {
    try {
      await dashboardService.deleteSearch(searchId);
      setSearchHistory(searchHistory.filter(s => s.id !== searchId));
    } catch (error) {
      console.error('Error deleting search:', error);
    }
  };

  const handleDeleteImage = async (imageId) => {
    try {
      await dashboardService.deleteImage(imageId);
      setImageHistory(imageHistory.filter(i => i.id !== imageId));
    } catch (error) {
      console.error('Error deleting image:', error);
    }
  };

  const handleExportCSV = async () => {
    try {
      await dashboardService.exportCSV();
    } catch (error) {
      console.error('Error exporting CSV:', error);
    }
  };

  const handleExportPDF = async () => {
    try {
      await dashboardService.exportPDF();
    } catch (error) {
      console.error('Error exporting PDF:', error);
    }
  };

  if (loading) {
    return <div className="loading">Loading dashboard...</div>;
  }

  return (
    <div className="dashboard-page">
      <div className="dashboard-header">
        <h1>Dashboard</h1>
        <div className="export-buttons">
          <button onClick={handleExportCSV} className="export-button">
            Export CSV
          </button>
          <button onClick={handleExportPDF} className="export-button">
            Export PDF
          </button>
        </div>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <h3>Total Searches</h3>
          <div className="stat-number">{stats.total_searches}</div>
        </div>
        <div className="stat-card">
          <h3>Total Images</h3>
          <div className="stat-number">{stats.total_images}</div>
        </div>
      </div>

      <div className="dashboard-content">
        <div className="section">
          <h2>Recent Searches</h2>
          <div className="history-list">
            {searchHistory.length === 0 ? (
              // --- START OF CHANGES ---
              <p>No searches yet. <Link to="/search" className="font-medium text-blue-600 dark:text-blue-400 hover:underline">Start searching!</Link></p>
              // --- END OF CHANGES ---
            ) : (
              searchHistory.map(search => (
                <div key={search.id} className="history-item">
                  <div className="item-content">
                    <h4>{search.query}</h4>
                    <p>{search.result_count} results</p>
                    <small>{new Date(search.created_at).toLocaleDateString()}</small>
                  </div>
                  <button
                    onClick={() => handleDeleteSearch(search.id)}
                    className="delete-button"
                  >
                    Delete
                  </button>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="section">
          <h2>Recent Images</h2>
          <div className="history-list">
            {imageHistory.length === 0 ? (
              // --- START OF CHANGES ---
              <p>No images yet. <Link to="/image" className="font-medium text-blue-600 dark:text-blue-400 hover:underline">Generate some!</Link></p>
              // --- END OF CHANGES ---
            ) : (
              imageHistory.map(image => (
                <div key={image.id} className="history-item image-item">
                  <img src={image.image_url} alt={image.prompt} />
                  <div className="item-content">
                    <h4>{image.prompt.length > 50 ? image.prompt.substring(0, 50) + '...' : image.prompt}</h4>
                    <small>{new Date(image.created_at).toLocaleDateString()}</small>
                  </div>
                  <button
                    onClick={() => handleDeleteImage(image.id)}
                    className="delete-button"
                  >
                    Delete
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default DashboardPage;
