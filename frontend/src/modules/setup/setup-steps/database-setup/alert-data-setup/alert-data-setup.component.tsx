import React, { FunctionComponent, useEffect, useState } from "react";
import { IDatabaseSetupConstituent } from "../database-setup.interfaces";
import { Modal, Button, Form, Table } from "react-bootstrap";
import { IQuery } from "./alert-data-setup.interfaces";
import { IAlertData } from "./alert-data-setup.interfaces";
import axios from "axios";

const API_ENDPOINT = process.env.REACT_APP_API_ENDPOINT || 'http://localhost:5007';

type IKeys = "name" | "file" | "threshold" | "alert";

const AlertDataSetup: FunctionComponent<IDatabaseSetupConstituent<IAlertData>> = ({ updateConfig }) => {
    const [queries, setQueries] = useState<IQuery[]>([]);
    const [gffFilePath, setGffFilePath] = useState<string | null>(null);
    const [showModal, setShowModal] = useState(false);

    const handleAddQuery = (newQuery: IQuery) => {
        setQueries((prev) => [...prev, newQuery]);
        setShowModal(false);
    };

    const handleRemoveQuery = (index: number) => {
        setQueries((prev) => prev.filter((_, i) => i !== index));
    };

    const handleGffFileChange = async (evt: React.ChangeEvent<HTMLInputElement>) => {
        const selectedFile = evt.target.files?.[0];
        if (selectedFile) {
            const formData = new FormData();
            formData.append('file', selectedFile);
            try {
                const uploadRes = await axios.post(`${API_ENDPOINT}/upload_gff`, formData, {
                    headers: { 'Content-Type': 'multipart/form-data' },
                });
                setGffFilePath(uploadRes.data.file_path);
            } catch (err) {
                console.error(err);
            }
        }
    };

    useEffect(() => {
        updateConfig({ queries, gff_file: gffFilePath || undefined });
    }, [queries, gffFilePath, updateConfig]);

    return (
        <div className="container">
            <h4 className="">Alert Sequences</h4>
            <p className="text-muted">Configure sequences to monitor during analysis.</p>
            {queries.length === 0 ? (
                <div className="text-center text-muted py-3">
                    No alert data added yet. Click '+' below to add alert data.
                </div>
            ) : (
                <Table striped bordered hover responsive className="mt-3">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>File Path</th>
                            <th>Threshold (x)</th>
                            <th>Alert</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {queries.map((q, i) => (
                            <tr key={i}>
                                <td>{q.name}</td>
                                <td>{q.file}</td>
                                <td>{q.depth_threshold}</td>
                                <td>{q.alert_on_depth ? "Yes" : "No"}</td>
                                <td>
                                    <Button
                                        variant="danger"
                                        size="sm"
                                        onClick={() => handleRemoveQuery(i)}
                                        aria-label="Remove sequence"
                                    >
                                        <i className="fa fa-trash-alt" />
                                    </Button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </Table>
            )}
            <Form.Group className="mb-3">
                <Form.Label>Optional: Upload GFF File for Regions of Interest</Form.Label>
                <Form.Control
                    type="file"
                    accept=".gff,.txt"
                    onChange={handleGffFileChange}
                />
            </Form.Group>
            <div className="text-center">
                <hr />
                <Button
                    variant="primary"
                    onClick={() => setShowModal(true)}
                    className="mt-3"
                ><i className="fa fa-plus" /></Button>
                <AddAlertModal
                    show={showModal}
                    onHide={() => setShowModal(false)}
                    onAdd={handleAddQuery}
                />
            </div>
        </div>
    );
};

type AddAlertModalProps = {
    show: boolean;
    onHide: () => void;
    onAdd: (newQuery: IQuery) => void;
};

const AddAlertModal: FunctionComponent<AddAlertModalProps> = ({ show, onHide, onAdd }) => {
    const [file, setFile] = useState<File | null>(null);
    const [filePath, setFilePath] = useState<string>("");
    const [headers, setHeaders] = useState<string[]>([]);
    const [selectedHeaders, setSelectedHeaders] = useState<string[]>([]);
    const [threshold, setThreshold] = useState("");
    const [alert, setAlert] = useState(false);
    const [errors, setErrors] = useState<{ [key: string]: string }>({});

    const handleFileChange = async (evt: React.ChangeEvent<HTMLInputElement>) => {
        const selectedFile = evt.target.files?.[0];
        if (selectedFile) {
            setFile(selectedFile);
            const formData = new FormData();
            formData.append('file', selectedFile);
            try {
                const uploadRes = await axios.post(`${API_ENDPOINT}/upload_fasta`, formData, {
                    headers: { 'Content-Type': 'multipart/form-data' },
                });
                const filePath = uploadRes.data.file_path;
                setFilePath(filePath);

                const headersRes = await axios.post(`${API_ENDPOINT}/parse_fasta_headers`, {
                    file_path: filePath
                }, {
                    headers: { 'Content-Type': 'application/json' }
                });
                setHeaders(headersRes.data);
                setSelectedHeaders([]);
            } catch (err) {
                console.error(err);
                setErrors({ file: 'Failed to parse file' });
            }
        }
    };

    const handleHeaderChange = (evt: React.ChangeEvent<HTMLSelectElement>) => {
        const options = evt.target.options;
        const selected: string[] = [];
        for (let i = 0; i < options.length; i++) {
            if (options[i].selected) {
                selected.push(options[i].value);
            }
        }
        setSelectedHeaders(selected);
    };

    const handleThresholdChange = (evt: React.ChangeEvent<HTMLInputElement>) => {
        setThreshold(evt.target.value);
    };

    const handleAlertChange = (evt: React.ChangeEvent<HTMLInputElement>) => {
        setAlert(evt.target.checked);
    };

    const validateForm = () => {
        const newErrors: { [key: string]: string } = {};
        if (!file) newErrors.file = "FASTA file is required.";
        if (selectedHeaders.length === 0) newErrors.header = "At least one header must be selected.";
        if (!threshold) {
            newErrors.threshold = "Threshold is required.";
        } else if (isNaN(parseFloat(threshold)) || parseFloat(threshold) < 0) {
            newErrors.threshold = "Threshold must be a positive number.";
        }
        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };

    const handleSubmit = () => {
        if (validateForm()) {
            const headersToUse = selectedHeaders.includes("ALL") ? headers : selectedHeaders;
            const newQueries = headersToUse.map(header => ({
                name: header,
                file: filePath,
                threshold,
                current_fold_change: 0,
                alert_on_depth: alert,
                alert_on_breadth: false,
                header
            }));
            newQueries.forEach(query => onAdd(query));
            // Reset form
            setFile(null);
            setFilePath("");
            setHeaders([]);
            setSelectedHeaders([]);
            setThreshold("");
            setAlert(false);
            setErrors({});
        }
    };

    return (
        <Modal show={show} onHide={onHide} centered>
            <Modal.Header closeButton>
                <Modal.Title>Add Alert Sequence</Modal.Title>
            </Modal.Header>
            <Modal.Body>
                <Form>
                    <Form.Group className="mb-3">
                        <Form.Label>FASTA File</Form.Label>
                        <Form.Control
                            type="file"
                            accept=".fasta,.fna,.fa,.fasta.gz,.fna.gz,.fa.gz"
                            onChange={handleFileChange}
                            isInvalid={!!errors.file}
                        />
                        <Form.Control.Feedback type="invalid">
                            {errors.file}
                        </Form.Control.Feedback>
                    </Form.Group>
                    {headers.length > 0 && (
                        <Form.Group className="mb-3">
                            <Form.Label>Select Sequence Headers</Form.Label>
                            <Form.Select
                                multiple
                                value={selectedHeaders}
                                onChange={handleHeaderChange}
                                isInvalid={!!errors.header}
                                size="sm"
                            >
                                <option value="ALL">ALL</option>
                                {headers.map((header, idx) => (
                                    <option key={idx} value={header}>{header}</option>
                                ))}
                            </Form.Select>
                            <Form.Text className="text-muted">
                                Use Ctrl/Cmd or Shift to select multiple headers. Select "ALL" to include all sequences.
                            </Form.Text>
                            <Form.Control.Feedback type="invalid">
                                {errors.header}
                            </Form.Control.Feedback>
                        </Form.Group>
                    )}
                    <Form.Group className="mb-3">
                        <Form.Label>Fold Coverage Threshold (x)</Form.Label>
                        <Form.Control
                            type="number"
                            value={threshold}
                            onChange={handleThresholdChange}
                            min="0"
                            isInvalid={!!errors.threshold}
                        />
                        <Form.Control.Feedback type="invalid">
                            {errors.threshold}
                        </Form.Control.Feedback>
                    </Form.Group>
                    <Form.Group className="mb-3">
                        <Form.Check
                            type="checkbox"
                            label="Enable Alert"
                            checked={alert}
                            onChange={handleAlertChange}
                        />
                    </Form.Group>
                </Form>
            </Modal.Body>
            <Modal.Footer>
                <Button variant="secondary" onClick={onHide}>
                    Cancel
                </Button>
                <Button variant="primary" onClick={handleSubmit}>
                    Add Sequences
                </Button>
            </Modal.Footer>
        </Modal>
    );
};

export default AlertDataSetup;