import React, { useState, useEffect } from 'react';
import { imageService } from '../services/imageService';

function ImagePage() {
  const [prompt, setPrompt] = useState('');
  const [width, setWidth] = useState(1024);
  const [height, setHeight] = useState(1024);
  const [generatedImage, setGeneratedImage] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    loadImageHistory();
  }, []);

  const loadImageHistory = async () => {
    try {
      const imageHistory = await imageService.getImageHistory();
      setHistory(imageHistory);
    } catch (error) {
      console.error('Error loading image history:', error);
    }
  };

  const handleGenerate = async (e) => {
    e.preventDefault();
    if (!prompt.trim()) return;

    setLoading(true);
    setError('');
    setGeneratedImage(null);

    try {
      const response = await imageService.generateImage({
        prompt: prompt.trim(),
        width: parseInt(width),
        height: parseInt(height)
      });

      setGeneratedImage(response);
      loadImageHistory(); // Refresh history
    } catch (error) {
      setError('Image generation failed. Please try again.');
      console.error('Image generation error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleHistoryClick = (historicalPrompt) => {
    setPrompt(historicalPrompt);
    setGeneratedImage(null);
  };

  const sizePresets = [
    { name: 'Square', width: 1024, height: 1024 },
    { name: 'Portrait', width: 768, height: 1024 },
    { name: 'Landscape', width: 1024, height: 768 },
    { name: 'Wide', width: 1280, height: 720 }
  ];

  return (
    <div className="image-page">
      <div className="image-header">
        <h1>AI Image Generation</h1>
        <p>Generate images using AI with detailed prompts</p>
      </div>

      <div className="image-container">
        <div className="generate-section">
          <form onSubmit={handleGenerate} className="image-form">
            <div className="form-group">
              <label htmlFor="prompt">Image Prompt</label>
              <textarea
                id="prompt"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="Describe the image you want to generate..."
                className="prompt-input"
                rows="4"
                disabled={loading}
              />
            </div>

            <div className="size-controls">
              <div className="size-presets">
                <label>Size Presets:</label>
                <div className="preset-buttons">
                  {sizePresets.map(preset => (
                    <button
                      key={preset.name}
                      type="button"
                      onClick={() => {
                        setWidth(preset.width);
                        setHeight(preset.height);
                      }}
                      className={`preset-button ${width === preset.width && height === preset.height ? 'active' : ''}`}
                    >
                      {preset.name}
                    </button>
                  ))}
                </div>
              </div>

              <div className="custom-size">
                <div className="size-input">
                  <label htmlFor="width">Width</label>
                  <input
                    type="number"
                    id="width"
                    value={width}
                    onChange={(e) => setWidth(e.target.value)}
                    min="256"
                    max="2048"
                    step="64"
                    disabled={loading}
                  />
                </div>
                <div className="size-input">
                  <label htmlFor="height">Height</label>
                  <input
                    type="number"
                    id="height"
                    value={height}
                    onChange={(e) => setHeight(e.target.value)}
                    min="256"
                    max="2048"
                    step="64"
                    disabled={loading}
                  />
                </div>
              </div>
            </div>

            {error && <div className="error-message">{error}</div>}

            <button
              type="submit"
              className="generate-button"
              disabled={loading || !prompt.trim()}
            >
              {loading ? 'Generating...' : 'Generate Image'}
            </button>
          </form>

          {loading && (
            <div className="loading-indicator">
              <div className="spinner"></div>
              <p>Generating your image...</p>
            </div>
          )}

          {generatedImage && (
            <div className="generated-result">
              <h3>Generated Image</h3>
              <div className="image-result">
                <img
                  src={generatedImage.image_url}
                  alt={generatedImage.prompt}
                  className="generated-image"
                />
                <div className="image-meta">
                  <p><strong>Prompt:</strong> {generatedImage.prompt}</p>
                  <p><strong>Size:</strong> {generatedImage.width} × {generatedImage.height}</p>
                  <p><strong>Generated:</strong> {new Date(generatedImage.timestamp).toLocaleString()}</p>
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="image-sidebar">
          <h2>Image History</h2>
          <div className="history-grid">
            {history.length === 0 ? (
              <p>No images generated yet.</p>
            ) : (
              history.slice(0, 12).map(item => (
                <div
                  key={item.id}
                  className="history-item image-history-item"
                  onClick={() => handleHistoryClick(item.prompt)}
                >
                  <img src={item.image_url} alt={item.prompt} />
                  <div className="history-overlay">
                    <div className="history-prompt">
                      {item.prompt.length > 30 ? item.prompt.substring(0, 30) + '...' : item.prompt}
                    </div>
                    <div className="history-date">
                      {new Date(item.created_at).toLocaleDateString()}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default ImagePage;
