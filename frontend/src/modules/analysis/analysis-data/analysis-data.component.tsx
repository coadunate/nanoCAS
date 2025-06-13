import React, { FunctionComponent, useEffect, useState, useMemo } from "react";
import { IAnalysisDataProps } from "./analysis-data.interfaces";
import { socket } from "../../../app.component";
import { Chart } from "react-google-charts";
import axios from "axios";
import { Dropdown, Modal, Button, OverlayTrigger, Tooltip } from "react-bootstrap";
import './analysis-data.component.css';

const API_ENDPOINT = process.env.REACT_APP_API_ENDPOINT || 'http://localhost:5007';

const POLLING_INTERVAL_MS = 10000;

const AnalysisDataComponent: FunctionComponent<IAnalysisDataProps> = ({ data }) => {
    const [analysisData, setAnalysisData] = useState(data);
    const [coverageData, setCoverageData] = useState<any[]>([]);
    const [coverageMap, setCoverageMap] = useState(new Map<string, any>());
    const [listenerRunning, setListenerRunning] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [fetchError, setFetchError] = useState<string | null>(null); // Still available but not used for this case
    const [metric, setMetric] = useState<'depth' | 'breadth'>('depth');
    const [showConfirmModal, setShowConfirmModal] = useState(false);
    type TimeUnit = 'seconds' | 'minutes' | 'hours' | 'days';
    const [timeUnit, setTimeUnit] = useState<TimeUnit>('seconds');
    const [isDatabaseReady, setIsDatabaseReady] = useState(false);

    const threshold = data.data.queries[0]?.threshold ? parseFloat(data.data.queries[0].threshold) : 100;

    const unitLabels: Record<TimeUnit, string> = {
        seconds: 's',
        minutes: 'min',
        hours: 'h',
        days: 'd'
    };

    const checkDatabaseStatus = async (projectId: string) => {
        try {
            const res = await axios.get(`${API_ENDPOINT}/check_database_status?projectId=${projectId}`);
            console.log("Database status response:", res.data);
            return res.data.is_ready;
        } catch (error) {
            console.error("Error checking database status:", error);
            return false; // Assume not ready if there's an error
        }
    };


    useEffect(() => {
        socket.emit('check_fastq_file_listener', { projectId: analysisData.data.projectId });

        const handleListenerStatus = (data: { projectId: string; is_running: boolean }) => {
            if (data.projectId === analysisData.data.projectId) setListenerRunning(data.is_running);
        };
        const handleListenerStarted = (data: { projectId: string }) => {
            if (data.projectId === analysisData.data.projectId) {
                setListenerRunning(true);
                setError(null);
            }
        };
        const handleListenerStopped = (data: { projectId: string }) => {
            if (data.projectId === analysisData.data.projectId) {
                setListenerRunning(false);
                setError(null);
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
            setError(null); // Clear previous errors before fetching
            try {
                const coverageRes = await axios.get(`${API_ENDPOINT}/get_coverage?projectId=${analysisData.data.projectId}`);
                const analysisRes = await axios.get(`${API_ENDPOINT}/get_analysis_info?uid=${analysisData.data.projectId}`);
                
                const newCoverageData = coverageRes.data;
                setCoverageData(newCoverageData);
                const map = new Map<string, any>();
                newCoverageData.forEach((entry: { timestamp: any; reference: any }) => {
                    const key = `${entry.timestamp}-${entry.reference}`;
                    map.set(key, entry);
                });
                setCoverageMap(map);

                if (analysisRes.data.status === 200) {
                    setAnalysisData(analysisRes.data);
                }
            } catch (err) {
                console.error("Error fetching data:", err);
                if (err.response && err.response.data && err.response.data.error) {
                    // Set specific error message from server
                    setError(err.response.data.error);
                } else if (err.response) {
                    // Handle other server errors with a generic message
                    setError("An error occurred while fetching data.");
                } else {
                    // Handle network errors
                    setError("Failed to connect to the server. Please check your network connection.");
                }
            }
            
            // Check database status
            const checkStats = await checkDatabaseStatus(analysisData.data.projectId);
            setIsDatabaseReady(checkStats);
            if (!checkStats) {
                setError("Database is not ready. Please wait for the database to be initialized.");
            }

        };

        fetchData();
        const interval = setInterval(fetchData, POLLING_INTERVAL_MS);

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
        if (times.length === 0) return [];

        const startTime = new Date(times[0]).getTime();
        const conversionFactors: Record<TimeUnit, number> = {
            seconds: 1,
            minutes: 60,
            hours: 3600,
            days: 86400
        };
        const factor = conversionFactors[timeUnit] || 1;

        const header = [{ type: 'number', label: `Elapsed Time (${unitLabels[timeUnit]})`, role: '' }];
        refs.forEach(ref => {
            header.push({ type: 'number', label: ref, role: '' });
            header.push({ type: 'string', label: 'for', role: 'tooltip' });
        });
        if (metric === "depth" && !isNaN(threshold)) {
            header.push({ type: 'number', label: 'Threshold', role: '' });
            header.push({ type: 'string', label: 'for', role: 'tooltip' });
        }

        const rows = times.map(time => {
            const elapsedSeconds = (new Date(time).getTime() - startTime) / 1000;
            const elapsedTime = elapsedSeconds / factor;
            const row: (number | string)[] = [elapsedTime];
            refs.forEach(ref => {
                const key = `${time}-${ref}`;
                const entry = coverageMap.get(key);
                const y = entry ? (metric === "depth" ? entry.depth : entry.breadth) : 0;
                const unit = metric === "depth" ? 'X' : '%';
                const tooltip = `Time: ${time}\nElapsed:${elapsedTime.toFixed(2)} ${unitLabels[timeUnit]}\n${ref}: ${y.toFixed(2)}${unit}`;
                row.push(y);
                row.push(tooltip);
            });
            if (metric === "depth" && !isNaN(threshold)) {
                row.push(threshold);
                row.push(`Threshold: ${threshold}`);
            }
            return row;
        });

        return [header, ...rows];
    };

    const formattedData = useMemo(() => formatCoverageData(), [coverageMap, metric, timeUnit]);

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

    const refs = [...new Set(coverageData.map(d => d.reference))];
    const numRefs = refs.length;

    const chartOptions = {
        title: `${metric === "depth" ? "Depth of Coverage" : "Breadth of Coverage"} Over Time`,
        hAxis: { title: `Elapsed Time (${unitLabels[timeUnit]})` },
        vAxis: { title: metric === "depth" ? 'Depth (X)' : 'Breadth (%)', minValue: 0 },
        legend: { position: 'bottom' },
        colors: ['#00B0BD', '#004E5A', '#FF6A45', '#27AE60'],
        chartArea: { width: '80%', height: '70%' },
        animation: { startup: true, duration: 1000, easing: 'out' },
        series: metric === "depth" && !isNaN(threshold) ? {
            [refs.length]: { lineDashStyle: [4, 4], color: 'red', lineWidth: 2, pointSize: 0 }
        } : {}
    };

    return (
        <div className="nano-analysis-container">
            <h2 className="nano-section-title">Analysis Dashboard</h2>
            <div className="nano-card nano-analysis-card">
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
                            <span className="nano-info-value">{analysisData.data.minion.split("/").filter(component => component !== '').join(' ➩ ')}</span>
                        </div>
                        <div className="nano-info-item">
                            <span className="nano-info-label">Status</span>
                            <span className={`nano-status-badge ${listenerRunning ? 'nano-status-running' : 'nano-status-stopped'}`}>
                                {listenerRunning ? 'Running' : 'Stopped'}
                            </span>
                        </div>
                    </div>
                    {error && <div className="nano-alert nano-alert-danger">{error}</div>}
                    <div className="nano-actions">
                        {listenerRunning ? (
                            <button className="btn btn-danger nano-btn" onClick={handleStopFileListener}>
                                <i className="fas fa-stop"></i> Stop Analysis
                            </button>
                        ) : (
                            isDatabaseReady ? (
                                <button className="btn btn-outline-primary nano-btn" onClick={handleStartFileListener}>
                                    <i className="fas fa-play"></i> Start Analysis
                                </button>
                            ) : (
                                <OverlayTrigger
                                    placement="top"
                                    overlay={<Tooltip id="database-not-found-tooltip">Database not found</Tooltip>}
                                >
                                    <span>
                                        <button className="btn btn-outline-primary nano-btn" disabled>
                                            <i className="fas fa-play"></i> Start Analysis
                                        </button>
                                    </span>
                                </OverlayTrigger>
                            )
                        )}
                        <button className="btn btn-outline-danger" onClick={handleRemoveAnalysis}>
                            <i className="fas fa-trash"></i> Remove Analysis
                        </button>
                    </div>
                </div>
            </div>

            {/* Coverage Plot */}
            <div className="nano-card nano-chart-card">
                <div className="nano-card-header d-flex justify-content-between align-items-center">
                    <h3 className="nano-card-title">Coverage Over Time</h3>
                    <div className="d-flex gap-2">
                        <Dropdown>
                            <Dropdown.Toggle variant="secondary" id="metricDropdown" size="sm">
                                {metric.charAt(0).toUpperCase() + metric.slice(1)}
                            </Dropdown.Toggle>
                            <Dropdown.Menu>
                                <Dropdown.Item onClick={() => setMetric('depth')}>Depth</Dropdown.Item>
                                <Dropdown.Item onClick={() => setMetric('breadth')}>Breadth</Dropdown.Item>
                            </Dropdown.Menu>
                        </Dropdown>
                        <Dropdown>
                            <Dropdown.Toggle variant="secondary" id="timeUnitDropdown" size="sm">
                                {timeUnit.charAt(0).toUpperCase() + timeUnit.slice(1)}
                            </Dropdown.Toggle>
                            <Dropdown.Menu>
                                <Dropdown.Item onClick={() => setTimeUnit('seconds')}>Seconds</Dropdown.Item>
                                <Dropdown.Item onClick={() => setTimeUnit('minutes')}>Minutes</Dropdown.Item>
                                <Dropdown.Item onClick={() => setTimeUnit('hours')}>Hours</Dropdown.Item>
                                <Dropdown.Item onClick={() => setTimeUnit('days')}>Days</Dropdown.Item>
                            </Dropdown.Menu>
                        </Dropdown>
                    </div>
                </div>
                <div className="nano-card-body">
                    {timeUnit && coverageData.length > 0 ? (
                        <Chart
                            key={metric}
                            chartType="LineChart"
                            data={formattedData}
                            options={chartOptions}
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
            <div className="nano-card nano-chart-card">
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
            <Modal show={showConfirmModal} onHide={cancelRemoveAnalysis}>
                <Modal.Header closeButton>
                    <Modal.Title>Confirm Removal</Modal.Title>
                </Modal.Header>
                <Modal.Body>
                    <p>Are you sure you want to remove this analysis? This action cannot be undone.</p>
                </Modal.Body>
                <Modal.Footer>
                    <Button variant="outline-secondary" onClick={cancelRemoveAnalysis}>
                        Cancel
                    </Button>
                    <Button variant="danger" onClick={confirmRemoveAnalysis}>
                        Remove
                    </Button>
                </Modal.Footer>
            </Modal>
        </div>
    );
};

export default AnalysisDataComponent;