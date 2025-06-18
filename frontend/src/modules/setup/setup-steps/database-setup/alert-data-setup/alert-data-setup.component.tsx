import React, { FunctionComponent, useEffect, useState } from "react";
import { IDatabaseSetupConstituent } from "../database-setup.interfaces";
import { Modal, Button, Form, Table } from "react-bootstrap";
import { IQuery } from "./alert-data-setup.interfaces";
import { IAlertData } from "./alert-data-setup.interfaces";

type IKeys = "name" | "file" | "threshold" | "alert";

const AlertDataSetup: FunctionComponent<IDatabaseSetupConstituent<IAlertData>> = ({ updateConfig }) => {
    const [queries, setQueries] = useState<IQuery[]>([]);
    const [showModal, setShowModal] = useState(false);

    const handleAddQuery = (newQuery: IQuery) => {
        setQueries((prev) => [...prev, newQuery]);
        setShowModal(false);
    };

    const handleRemoveQuery = (index: number) => {
        setQueries((prev) => prev.filter((_, i) => i !== index));
    };

    useEffect(() => {
        updateConfig({ queries });
    }, [queries, updateConfig]);

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
                                <td>{q.threshold}</td>
                                <td>{q.alert ? "Yes" : "No"}</td>
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
    const [newQuery, setNewQuery] = useState<IQuery>({
        name: "",
        file: "",
        threshold: "",
        current_fold_change: 0,
        alert: false,
        header: ""
    });
    const [errors, setErrors] = useState<{ [key: string]: string }>({});

    const handleChange = (key: keyof IQuery) => (evt: React.ChangeEvent<HTMLInputElement>) => {
        const value = evt.target.type === "checkbox" ? evt.target.checked : evt.target.value;
        setNewQuery((prev) => ({ ...prev, [key]: value }));
        setErrors((prev) => ({ ...prev, [key]: "" }));
    };

    const validateForm = () => {
        const newErrors: { [key: string]: string } = {};
        if (!newQuery.name) newErrors.name = "Sequence name is required.";
        if (!newQuery.file) newErrors.file = "File path is required.";
        if (!newQuery.threshold) {
            newErrors.threshold = "Threshold is required.";
        } else if (isNaN(parseFloat(newQuery.threshold)) || parseFloat(newQuery.threshold) < 0) {
            newErrors.threshold = "Threshold must be a positive number.";
        }
        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };

    const handleSubmit = () => {
        if (validateForm()) {
            onAdd(newQuery);
            setNewQuery({ name: "", file: "", threshold: "", alert: false, current_fold_change: 0, header: "" });
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
                        <Form.Label>Sequence Identifier</Form.Label>
                        <Form.Control
                            type="text"
                            placeholder="e.g., Pathogen X"
                            value={newQuery.name}
                            onChange={handleChange("name")}
                            isInvalid={!!errors.name}
                        />
                        <Form.Control.Feedback type="invalid">
                            {errors.name}
                        </Form.Control.Feedback>
                    </Form.Group>
                    <Form.Group className="mb-3">
                        <Form.Label>Sequence File Path</Form.Label>
                        <Form.Control
                            type="text"
                            placeholder="/path/to/file.fasta"
                            value={newQuery.file}
                            onChange={handleChange("file")}
                            isInvalid={!!errors.file}
                        />
                        <Form.Control.Feedback type="invalid">
                            {errors.file}
                        </Form.Control.Feedback>
                    </Form.Group>
                    <Form.Group className="mb-3">
                        <Form.Label>Fold Coverage Threshold (x)</Form.Label>
                        <Form.Control
                            type="number"
                            placeholder="e.g., 10"
                            value={newQuery.threshold}
                            onChange={handleChange("threshold")}
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
                            checked={newQuery.alert}
                            onChange={handleChange("alert")}
                        />
                    </Form.Group>
                </Form>
            </Modal.Body>
            <Modal.Footer>
                <Button variant="secondary" onClick={onHide}>
                    Cancel
                </Button>
                <Button variant="primary" onClick={handleSubmit}>
                    Add Sequence
                </Button>
            </Modal.Footer>
        </Modal>
    );
};

export default AlertDataSetup;