import React, { FunctionComponent } from 'react';
import { Inanocas } from "./home.interfaces";
import { gotoLoc } from "../../utils/utils";
import './home.component.css';

const nanocas_config: Inanocas = {
    title: "nanoCAS",
    tagline: "Nanopore Classification & Alerting System",
    description: "nanoCAS is a web application designed to run simultaneously with the Nanopore DNA sequencer. " +
        "This application provides an alerting system through which scientists performing DNA " +
        "sequencing runs can be notified when sequences of interest arise in their sample. " +
        "This enables researchers to use their time more efficiently by allowing them " +
        "to focus on other tasks rather than waiting for significant sequences to appear.",
    version: '1.0.0'
}

const HomeComponent: FunctionComponent = () => {
    return (
        <div className="nano-home-container">
            <div className="nano-hero">
                <div className="nano-hero-content">
                    <h1 className="nano-hero-title">{nanocas_config.title}</h1>
                    <p className="nano-hero-tagline">{nanocas_config.tagline}</p>
                    <p className="nano-hero-version">Version {nanocas_config.version}</p>
                    <div className="nano-hero-buttons">
                        <button onClick={() => gotoLoc('/setup')} className="btn btn-primary nano-btn">
                            Start New Analysis
                        </button>
                        <button onClick={() => gotoLoc('/analysis')} className="btn btn-outline-primary nano-btn">
                            View Analyses
                        </button>
                    </div>
                </div>
            </div>
            
            <div className="nano-section">
                <div className="nano-container">
                    <h2 className="nano-section-title">About nanoCAS</h2>
                    <div className="nano-description">
                        <p className="nano-description-text">
                            {nanocas_config.description}
                        </p>
                    </div>
                    
                    <div className="nano-features">
                        <div className="nano-feature-card">
                            <div className="nano-feature-icon">
                                <i className="fas fa-bell"></i>
                            </div>
                            <h3 className="nano-feature-title">Real-time Alerts</h3>
                            <p className="nano-feature-description">
                                Receive notifications when sequences of interest are detected in your samples.
                            </p>
                        </div>
                        
                        <div className="nano-feature-card">
                            <div className="nano-feature-icon">
                                <i className="fas fa-chart-line"></i>
                            </div>
                            <h3 className="nano-feature-title">Live Monitoring</h3>
                            <p className="nano-feature-description">
                                Track sequence coverage and match percentages in real-time.
                            </p>
                        </div>
                        
                        <div className="nano-feature-card">
                            <div className="nano-feature-icon">
                                <i className="fas fa-cog"></i>
                            </div>
                            <h3 className="nano-feature-title">Easy Setup</h3>
                            <p className="nano-feature-description">
                                Configure your analysis parameters with a simple, intuitive interface.
                            </p>
                        </div>
                    </div>
                </div>
            </div>
            
            <div className="nano-cta-section">
                <div className="nano-container">
                    <h2 className="nano-cta-title">Ready to get started?</h2>
                    <p className="nano-cta-text">
                        Set up your Nanopore analysis in minutes and start receiving alerts for sequences of interest.
                    </p>
                    <button onClick={() => gotoLoc('/setup')} className="btn btn-accent nano-cta-button">
                        Start New Analysis
                    </button>
                </div>
            </div>
        </div>
    );
}

export default HomeComponent;
