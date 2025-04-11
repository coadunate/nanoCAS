import React from 'react';
import { Link } from 'react-router-dom';
import '../styles/header.css';

// import logo png file
import logo from '../assets/nanoCAS_icon.png';

const Header: React.FC = () => {
  return (
    <header className="nano-header">
      <div className="nano-header-container">
        <div className="nano-logo-container">
          <Link to="/">
            <img 
              src={logo} 
              alt="nanoCAS" 
              className="nano-logo" 
            />
          </Link>
        </div>
        <nav className="nano-nav">
          <ul className="nano-nav-list">
            <li className="nano-nav-item">
              <Link to="/" className="nano-nav-link">Home</Link>
            </li>
            <li className="nano-nav-item">
              <Link to="/setup" className="nano-nav-link">Setup</Link>
            </li>
            <li className="nano-nav-item">
              <Link to="/analysis" className="nano-nav-link">Analysis</Link>
            </li>
          </ul>
        </nav>
      </div>
    </header>
  );
};

export default Header;
