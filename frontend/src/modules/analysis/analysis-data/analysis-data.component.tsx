import React, { FunctionComponent, useEffect, useState } from "react";
import { IAnalysisDataProps } from "./analysis-data.interfaces";
import { socket } from "../../../app.component";
import ChartComponent from "./chart/chart.component";
import { Chart } from "react-google-charts";
import axios from "axios";
import './analysis-data.component.css';

const AnalysisDataComponent: FunctionComponent<IAnalysisDataProps> = ({ data }) => {
    const analysis_data = data.data;
    const [listenerRunning, setListenerRunning] = useState(false);
    const [error, setError] = useState("");
    const [coverageData, setCoverageData] = useState<any[]>([]);
    const [showConfirmModal, setShowConfirmModal] = useState(false);

    useEffect(() => {
        // File listener status
        socket.emit('check_fastq_file_listener', { projectId: analysis_data.projectId });
        
        const handleListenerStatus = (data: { projectId: string; is_running: boolean }) => {
            if (data.projectId === analysis_data.projectId) setListenerRunning(data.is_running);
        };
        
        const handleListenerStarted = (data: { projectId: string }) => {
            if (data.projectId === analysis_data.projectId) {
                setListenerRunning(true);
                setError("");
            }
        };
        
        const handleListenerStopped = (data: { projectId: string }) => {
            if (data.projectId === analysis_data.projectId) {
                setListenerRunning(false);
                setError("");
            }
        };
        
        const handleListenerError = (data: { projectId: string; error: string }) => {
            if (data.projectId === analysis_data.projectId) {
                setError(data.error);
                setListenerRunning(false);
            }
        };
        
        socket.on('fastq_file_listener_status', handleListenerStatus);
        socket.on('fastq_file_listener_started', handleListenerStarted);
        socket.on('fastq_file_listener_stopped', handleListenerStopped);
        socket.on('fastq_file_listener_error', handleListenerError);

        // Fetch coverage data periodically
        const fetchCoverage = async () => {
            try {
                const res = await axios.get(`http://localhost:5007/get_coverage?projectId=${analysis_data.projectId}`);
                setCoverageData(res.data);
            } catch (err) {
                console.error("Error fetching coverage:", err);
            }
        };
        
        fetchCoverage();
        const interval = setInterval(fetchCoverage, 10000); // Update every 10 seconds
        
        return () => {
            clearInterval(interval);
            socket.off('fastq_file_listener_status', handleListenerStatus);
            socket.off('fastq_file_listener_started', handleListenerStarted);
            socket.off('fastq_file_listener_stopped', handleListenerStopped);
            socket.off('fastq_file_listener_error', handleListenerError);
        };
    }, [analysis_data.projectId]);

    const handleStartFileListener = () => {
        socket.emit('start_fastq_file_listener', {
            minion_location: analysis_data.minion,
            projectId: analysis_data.projectId
        });
    };

    const handleStopFileListener = () => {
        socket.emit('stop_fastq_file_listener', { projectId: analysis_data.projectId });
    };
    
    const handleRemoveAnalysis = () => {
        setShowConfirmModal(true);
    };
    
    const confirmRemoveAnalysis = () => {
        socket.emit('remove_analysis', { projectId: analysis_data.projectId });
        setShowConfirmModal(false);
        // Redirect to analysis list after a short delay
        setTimeout(() => {
            window.location.href = '/analysis';
        }, 1000);
    };
    
    const cancelRemoveAnalysis = () => {
        setShowConfirmModal(false);
    };

    // Match ratio bar plot data
    let matchData = [["Name", "Match Percentage (%)", "Threshold (%)"]];
    for (let query of analysis_data.queries) {
        const threshNum = parseFloat(query.threshold);
        const currVal = query.current_value || 0;
        matchData.push([query.name, currVal, threshNum]);
    }

    // Coverage line chart data
    const formatCoverageData = () => {
        const refs = [...new Set(coverageData.map(d => d.reference))];
        const times = [...new Set(coverageData.map(d => d.timestamp))].sort();
        const header = ["Time", ...refs];
        const rows = times.map(time => {
            const row = [time];
            refs.forEach(ref => {
                const entry = coverageData.find(d => d.timestamp === time && d.reference === ref);
                row.push(entry ? entry.coverage : 0);
            });
            return row;
        });
        return [header, ...rows];
    };

    return (
        <div className="nano-analysis-container">
            <h2 className="nano-section-title">Analysis Dashboard</h2>
            <div className="ont-card nano-analysis-card">
                <div className="nano-card-header">
                    <h3 className="nano-card-title">Analysis Information</h3>
                </div>
                <div className="nano-card-body">
                    <div className="nano-info-grid">
                        <div className="nano-info-item">
                            <span className="nano-info-label">Analysis ID</span>
                            <span className="nano-info-value">{analysis_data.projectId}</span>
                        </div>
                        <div className="nano-info-item">
                            <span className="nano-info-label">MinION Path</span>
                            <span className="nano-info-value">{analysis_data.minion}</span>
                        </div>
                        <div className="nano-info-item">
                            <span className="nano-info-label">Device</span>
                            <span className="nano-info-value">{analysis_data.device || "Not specified"}</span>
                        </div>
                        <div className="nano-info-item">
                            <span className="nano-info-label">Status</span>
                            <span className={`ont-status-badge ${listenerRunning ? 'ont-status-running' : 'ont-status-stopped'}`}>
                                {listenerRunning ? 'Running' : 'Stopped'}
                            </span>
                        </div>
                    </div>
                    
                    {error && <div className="ont-alert nano-alert-danger">{error}</div>}
                    
                    <div className="nano-actions">
                        {listenerRunning ? (
                            <button className="btn btn-danger nano-btn" onClick={handleStopFileListener}>
                                <i className="fas fa-stop"></i> Stop File Listener
                            </button>
                        ) : (
                            <button className="btn btn-primary nano-btn" onClick={handleStartFileListener}>
                                <i className="fas fa-play"></i> Start File Listener
                            </button>
                        )}
                        <button className="btn btn-outline-danger nano-btn" onClick={handleRemoveAnalysis}>
                            <i className="fas fa-trash"></i> Remove Analysis
                        </button>
                    </div>
                </div>
            </div>
            
            <div className="ont-card nano-chart-card">
                <div className="nano-card-header">
                    <h3 className="nano-card-title">Sequences Match Visualization</h3>
                </div>
                <div className="nano-card-body">
                    <ChartComponent queries_data={matchData} />
                </div>
            </div>
            
            <div className="ont-card nano-chart-card">
                <div className="nano-card-header">
                    <h3 className="nano-card-title">Coverage Over Time</h3>
                </div>
                <div className="nano-card-body">
                    {coverageData.length > 0 ? (
                        <Chart
                            chartType="LineChart"
                            data={formatCoverageData()}
                            options={{
                                title: "Average Coverage Depth Over Time",
                                hAxis: { title: "Time" },
                                vAxis: { title: "Average Coverage Depth (reads/position)", minValue: 0 },
                                legend: { position: "bottom" },
                                colors: ['#00B0BD', '#004E5A', '#FF6A45', '#27AE60'],
                                chartArea: { width: '80%', height: '70%' },
                                animation: {
                                    startup: true,
                                    duration: 1000,
                                    easing: 'out'
                                }
                            }}
                            width="100%"
                            height="400px"
                        />
                    ) : (
                        <div className="nano-empty-state">
                            <p>No coverage data available yet.</p>
                            <p className="nano-empty-hint">Start the file listener to begin collecting coverage data.</p>
                        </div>
                    )}
                </div>
            </div>
            
            {showConfirmModal && (
                <div className="nano-modal-overlay">
                    <div className="nano-modal">
                        <div className="nano-modal-header">
                            <h4 className="nano-modal-title">Confirm Removal</h4>
                        </div>
                        <div className="nano-modal-body">
                            <p>Are you sure you want to remove this analysis? This action cannot be undone.</p>
                        </div>
                        <div className="nano-modal-footer">
                            <button className="btn btn-outline-secondary nano-btn" onClick={cancelRemoveAnalysis}>
                                Cancel
                            </button>
                            <button className="btn btn-danger nano-btn" onClick={confirmRemoveAnalysis}>
                                Remove
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default AnalysisDataComponent;
