import React, { useState, useEffect } from 'react';
import { searchService } from '../services/searchService';

function SearchPage() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    loadSearchHistory();
  }, []);

  const loadSearchHistory = async () => {
    try {
      const searchHistory = await searchService.getSearchHistory();
      setHistory(searchHistory);
    } catch (error) {
      console.error('Error loading search history:', error);
    }
  };

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError('');

    try {
      const response = await searchService.performSearch({
        query: query.trim(),
        max_results: 10
      });

      setResults(response.results);
      loadSearchHistory(); // Refresh history
    } catch (error) {
      setError('Search failed. Please try again.');
      console.error('Search error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleHistoryClick = (historicalQuery) => {
    setQuery(historicalQuery);
    setResults([]);
  };

  return (
    <div className="search-page">
      <div className="search-header">
        <h1>Web Search</h1>
        <p>Search the web using AI-powered tools</p>
      </div>

      <div className="search-container">
        <form onSubmit={handleSearch} className="search-form">
          <div className="search-input-group">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Enter your search query..."
              className="search-input"
              disabled={loading}
            />
            <button
              type="submit"
              className="search-button"
              disabled={loading || !query.trim()}
            >
              {loading ? 'Searching...' : 'Search'}
            </button>
          </div>
        </form>

        {error && <div className="error-message">{error}</div>}

        <div className="search-content">
          <div className="search-results">
            <h2>Search Results</h2>
            {results.length === 0 && !loading && (
              <p>No results yet. Enter a query to search the web.</p>
            )}

            {results.map((result, index) => (
              <div key={index} className="result-item">
                <h3>
                  <a href={result.url} target="_blank" rel="noopener noreferrer">
                    {result.title}
                  </a>
                </h3>
                <p className="result-url">{result.url}</p>
                <p className="result-snippet">{result.snippet}</p>
                {result.published_date && (
                  <small className="result-date">
                    Published: {new Date(result.published_date).toLocaleDateString()}
                  </small>
                )}
              </div>
            ))}
          </div>

          <div className="search-sidebar">
            <h2>Search History</h2>
            <div className="history-list">
              {history.length === 0 ? (
                <p>No search history yet.</p>
              ) : (
                history.slice(0, 10).map(item => (
                  <div
                    key={item.id}
                    className="history-item clickable"
                    onClick={() => handleHistoryClick(item.query)}
                  >
                    <div className="history-query">{item.query}</div>
                    <div className="history-meta">
                      {item.result_count} results • {new Date(item.created_at).toLocaleDateString()}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default SearchPage;
