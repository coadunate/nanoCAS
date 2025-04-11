import React from 'react';
import { Link } from 'react-router-dom';
import '../styles/footer.css';

import logo from '../assets/nanoCAS_icon.png';

const Footer: React.FC = () => {
  return (
    <footer className="nano-footer">
      <div className="nano-footer-container">
        <div className="nano-footer-content">
          <div className="nano-footer-logo">
            <img 
              src={logo}
              alt="Oxford Nanopore Technologies" 
              className="nano-logo-footer" 
            />
          </div>
          <div className="nano-footer-info">
            <p>nanoCAS - Nanopore Classification & Alerting System</p>
            <p>© {new Date().getFullYear()} nanoCAS | Coadunate</p>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
