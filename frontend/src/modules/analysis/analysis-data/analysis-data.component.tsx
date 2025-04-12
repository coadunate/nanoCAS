import React, { FunctionComponent, useEffect, useState } from "react";
import { IAnalysisDataProps } from "./analysis-data.interfaces";
import { socket } from "../../../app.component";
import { Chart } from "react-google-charts";
import axios from "axios";
import './analysis-data.component.css';

const AnalysisDataComponent: FunctionComponent<IAnalysisDataProps> = ({ data }) => {
    const [analysisData, setAnalysisData] = useState(data);
    const [coverageData, setCoverageData] = useState<any[]>([]);
    const [listenerRunning, setListenerRunning] = useState(false);
    const [error, setError] = useState("");
    const [metric, setMetric] = useState<'avg_depth' | 'breadth'>('avg_depth');
    const [showConfirmModal, setShowConfirmModal] = useState(false);

    useEffect(() => {
        socket.emit('check_fastq_file_listener', { projectId: analysisData.data.projectId });

        const handleListenerStatus = (data: { projectId: string; is_running: boolean }) => {
            if (data.projectId === analysisData.data.projectId) setListenerRunning(data.is_running);
        };
        const handleListenerStarted = (data: { projectId: string }) => {
            if (data.projectId === analysisData.data.projectId) {
                setListenerRunning(true);
                setError("");
            }
        };
        const handleListenerStopped = (data: { projectId: string }) => {
            if (data.projectId === analysisData.data.projectId) {
                setListenerRunning(false);
                setError("");
            }
        };
        const handleListenerError = (data: { projectId: string; error: string }) => {
            if (data.projectId === analysisData.data.projectId) {
                setError(data.error);
                setListenerRunning(false);
            }
        };

        socket.on('fastq_file_listener_status', handleListenerStatus);
        socket.on('fastq_file_listener_started', handleListenerStarted);
        socket.on('fastq_file_listener_stopped', handleListenerStopped);
        socket.on('fastq_file_listener_error', handleListenerError);

        const fetchData = async () => {
            try {
                const coverageRes = await axios.get(`http://localhost:5007/get_coverage?projectId=${analysisData.data.projectId}`);
                setCoverageData(coverageRes.data);

                const analysisRes = await axios.get(`http://localhost:5007/get_analysis_info?uid=${analysisData.data.projectId}`);
                if (analysisRes.data.status === 200) {
                    setAnalysisData(analysisRes.data);
                }
            } catch (err) {
                console.error("Error fetching data:", err);
            }
        };

        fetchData();
        const interval = setInterval(fetchData, 10000);

        return () => {
            clearInterval(interval);
            socket.off('fastq_file_listener_status', handleListenerStatus);
            socket.off('fastq_file_listener_started', handleListenerStarted);
            socket.off('fastq_file_listener_stopped', handleListenerStopped);
            socket.off('fastq_file_listener_error', handleListenerError);
        };
    }, [analysisData.data.projectId]);

    const formatCoverageData = () => {
        const refs = [...new Set(coverageData.map(d => d.reference))];
        const times = [...new Set(coverageData.map(d => d.timestamp))].sort();
        const header = ["Time", ...refs];
        const rows = times.map(time => {
            const row = [time];
            refs.forEach(ref => {
                const entry = coverageData.find(d => d.timestamp === time && d.reference === ref);
                row.push(entry ? entry[metric] : 0);
            });
            return row;
        });
        return [header, ...rows];
    };

    const getSankeyData = () => {
        if (coverageData.length === 0) return [['From', 'To', 'Weight']];
        const timestamps = coverageData.map(d => new Date(d.timestamp).getTime());
        const maxTimestamp = Math.max(...timestamps);
        const latestData = coverageData.filter(d => new Date(d.timestamp).getTime() === maxTimestamp);
        return [
            ['From', 'To', 'Weight'],
            ...latestData.map(entry => ['Sequencing Run', entry.reference, entry.read_count])
        ];
    };

    const handleStartFileListener = () => {
        socket.emit('start_fastq_file_listener', {
            minion_location: analysisData.data.minion,
            projectId: analysisData.data.projectId
        });
    };

    const handleStopFileListener = () => {
        socket.emit('stop_fastq_file_listener', { projectId: analysisData.data.projectId });
    };

    const handleRemoveAnalysis = () => {
        setShowConfirmModal(true);
    };

    const confirmRemoveAnalysis = () => {
        socket.emit('remove_analysis', { projectId: analysisData.data.projectId });
        setShowConfirmModal(false);
        setTimeout(() => {
            window.location.href = '/analysis';
        }, 1000);
    };

    const cancelRemoveAnalysis = () => {
        setShowConfirmModal(false);
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
                            <span className="nano-info-value">{analysisData.data.projectId}</span>
                        </div>
                        <div className="nano-info-item">
                            <span className="nano-info-label">MinION Path</span>
                            <span className="nano-info-value">{analysisData.data.minion}</span>
                        </div>
                        <div className="nano-info-item">
                            <span className="nano-info-label">Device</span>
                            <span className="nano-info-value">{analysisData.data.device || "Not specified"}</span>
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

            {/* Coverage Plot */}
            <div className="ont-card nano-chart-card">
                <div className="nano-card-header">
                    <h3 className="nano-card-title">Coverage Over Time</h3>
                    <select
                        value={metric}
                        onChange={(e) => setMetric(e.target.value as 'avg_depth' | 'breadth')}
                        className="form-control w-auto d-inline-block ml-2"
                    >
                        <option value="avg_depth">Average Depth</option>
                        <option value="breadth">Breadth of Coverage (%)</option>
                    </select>
                </div>
                <div className="nano-card-body">
                    {coverageData.length > 0 ? (
                        <Chart
                            chartType="LineChart"
                            data={formatCoverageData()}
                            options={{
                                title: metric === 'avg_depth' ? 'Average Coverage Depth Over Time' : 'Breadth of Coverage Over Time',
                                hAxis: { title: "Time" },
                                vAxis: { 
                                    title: metric === 'avg_depth' ? 'Average Depth (reads/position)' : 'Breadth (%)', 
                                    minValue: 0,
                                    maxValue: metric === 'breadth' ? 100 : undefined
                                },
                                legend: { position: "bottom" },
                                colors: ['#00B0BD', '#004E5A', '#FF6A45', '#27AE60'],
                                chartArea: { width: '80%', height: '70%' },
                                animation: { startup: true, duration: 1000, easing: 'out' }
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

            {/* Sankey Plot */}
            <div className="ont-card nano-chart-card">
                <div className="nano-card-header">
                    <h3 className="nano-card-title">Alert Sequences Distribution</h3>
                </div>
                <div className="nano-card-body">
                    {coverageData.length > 0 ? (
                        <Chart
                            chartType="Sankey"
                            data={getSankeyData()}
                            options={{
                                sankey: {
                                    node: {
                                        nodePadding: 50,
                                        width: 20,
                                        label: { fontName: 'Arial', fontSize: 14, color: '#000' },
                                        colors: ['#00B0BD', '#004E5A', '#FF6A45', '#27AE60'],
                                    },
                                    link: {
                                        colorMode: 'gradient',
                                        colors: ['#a6cee3', '#b2df8a', '#fb9a99', '#fdbf6f'],
                                    },
                                },
                            }}
                            width="100%"
                            height="400px"
                        />
                    ) : (
                        <div className="nano-empty-state">
                            <p>No data available yet for Sankey plot.</p>
                        </div>
                    )}
                </div>
            </div>

            {/* Confirmation Modal */}
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