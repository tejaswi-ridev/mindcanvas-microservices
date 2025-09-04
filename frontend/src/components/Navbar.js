import React from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useTheme } from '../contexts/ThemeContext';

function Navbar() {
  const { user, logout } = useAuth();
  const { isDarkMode, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const isActive = (path) => location.pathname === path;

  return (
    <nav className="navbar">
      <div className="navbar-container">
        <div className="navbar-brand">
          <Link to="/dashboard">
            <h2>MindCanvas</h2>
          </Link>
        </div>

        <div className="navbar-links">
          <Link
            to="/dashboard"
            className={`nav-link ${isActive('/dashboard') ? 'active' : ''}`}
          >
            Dashboard
          </Link>
          <Link
            to="/search"
            className={`nav-link ${isActive('/search') ? 'active' : ''}`}
          >
            Search
          </Link>
          <Link
            to="/image"
            className={`nav-link ${isActive('/image') ? 'active' : ''}`}
          >
            Generate Images
          </Link>
        </div>

        <div className="navbar-actions">
          <button onClick={toggleTheme} className="theme-toggle">
            {isDarkMode ? '🌞' : '🌙'}
          </button>

          <div className="user-menu">
            <span className="user-name">{user?.full_name || user?.email}</span>
            <button onClick={handleLogout} className="logout-button">
              Logout
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
}

export default Navbar;
