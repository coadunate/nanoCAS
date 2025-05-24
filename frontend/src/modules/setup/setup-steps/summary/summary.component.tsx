import React, { FunctionComponent, useState } from 'react';
import { IDatabseSetupInput, ILocationConfig } from "../database-setup/database-setup.interfaces";
import { IQuery } from "../database-setup/additional-sequences-setup/additional-sequences-setup.interfaces";
import axios from "axios";
import { socket } from "../../../../app.component";
import { IAlertNotifSetupInput } from '../alert-notif-setup/alert-notif-setup.interfaces';

const VALIDATION_STATES = {
    NOT_STARTED: 0,
    PENDING: 1,
    VALIDATED: 2,
    NOT_VALID: 3
}

type ISummaryComponentProps = {
    databaseSetupInput: IDatabseSetupInput
    alertNotifSetupInput: IAlertNotifSetupInput
}

const validateLocations = (queries: IQuery[], locations: ILocationConfig) => {
    let queryFiles = ""
    queries.map(query => {
        queryFiles += query.file + ';'
        return null;
    })
    let locationData = new FormData();
    locationData.append('minION', locations.minionLocation);
    locationData.append('Queries', queryFiles);

    return axios({
        method: 'POST',
        url: 'http://localhost:5007/validate_locations',
        data: locationData,
        headers: {"Content-Type": "multipart/form-data"},
    })
}

const getUniqueUID = (locations: ILocationConfig) => {
    let locationData = new FormData();
    locationData.append('minION', locations.minionLocation);

    return axios({
        method: "POST",
        url: 'http://localhost:5007/get_uid',
        data: locationData
    })
}

const SummaryComponent: FunctionComponent<ISummaryComponentProps> = ({ databaseSetupInput, alertNotifSetupInput }) => {
    const [success, setSuccess] = useState("");
    const [error, setError] = useState("");
    const [validationState, setValidationState] = useState(VALIDATION_STATES.NOT_STARTED);
    const [started, setStarted] = useState(false);
    const [uid, setUID] = useState("");

    // Additional databases
    const add_databases = databaseSetupInput.queries.queries;

    const initiateDatabaseCreation = async (e: React.MouseEvent<HTMLButtonElement, MouseEvent>) => {
        e.preventDefault();
        setStarted(true);

        try {
            // Validate locations
            const res = await validateLocations(add_databases, databaseSetupInput.locations);
            const v_code = res.data.code;

            if (v_code === 0) { // Locations are valid
                // Generate UUID only when initiating
                const res_uid = await getUniqueUID(databaseSetupInput.locations);
                const newUID = res_uid.data.uid;
                setUID(newUID);
                setValidationState(VALIDATION_STATES.VALIDATED);

                // Proceed with database creation
                socket.emit('log', "Locations are valid", "INFO");
                let dbInfo = {
                    minion: databaseSetupInput.locations.minionLocation,
                    queries: add_databases,
                    projectId: newUID,
                    device: databaseSetupInput.device.device,
                    fileType: databaseSetupInput.fileType,
                    alertNotifConfig: alertNotifSetupInput
                };

                socket.emit('log', dbInfo, "DEBUG");
                socket.emit('download_database', dbInfo, () => {
                    socket.emit('log', "Creating database...", "INFO");
                });
                let _url = 'http://' + window.location.hostname + ":" + window.location.port + '/analysis/' + newUID;
                setSuccess("Creating database... You can view the analysis <a href='" + _url + "'>here</a>");
            } else {
                setValidationState(VALIDATION_STATES.NOT_VALID);
                setError("Locations are not valid");
            }
        } catch (err) {
            setError("An error occurred during setup");
            console.error(err);
        }
    };

    return (
        <div className="container text-center">
            <div className="vspacer-20" />
            {success && (
                <div className="alert alert-success text-left" dangerouslySetInnerHTML={{ __html: "SUCCESS -- " + success }} />
            )}
            {error && <div className="alert alert-danger text-left">ERROR –– {error}</div>}
            <h4>Setup Summary</h4>
            <p>Review your configuration below:</p>
            <div className="vspacer-20" />
            <table className="table table-bordered">
                <thead className="thead-light">
                <tr><th colSpan={3}>Database Selection</th></tr>
                </thead>
                <tbody>
                {add_databases.length > 0 ? (
                    add_databases.map((query, idx) => (
                        <tr key={idx}>
                            <th>{idx === 0 ? "Additional Sequences" : ""}</th>
                            <td>Name: {query.name}</td>
                            <td>Threshold: {query.threshold}%</td>
                        </tr>
                    ))
                ) : (
                    <tr><td colSpan={3}>No additional sequences provided.</td></tr>
                )}
                </tbody>
                <thead className="thead-light">
                <tr><th colSpan={3}>Configuration</th></tr>
                </thead>
                <tbody>
                <tr><th>MinION Directory</th><td colSpan={2}>{databaseSetupInput.locations.minionLocation}</td></tr>
                <tr><th>Sequencing Device</th><td colSpan={2}>{databaseSetupInput.device.device || "Not provided"}</td></tr>
                <tr><th>File Type</th><td colSpan={2}>{databaseSetupInput.fileType}</td></tr>
                </tbody>
                <thead className="thead-light">
                <tr><th colSpan={3}>Alert Notification</th></tr>
                </thead>
                <tbody>
                <tr><th>Sender</th><td colSpan={2}>{alertNotifSetupInput.sender}</td></tr>
                <tr><th>Recipient</th><td colSpan={2}>{alertNotifSetupInput.recipient}</td></tr>
                <tr><th>SMTP Server</th><td colSpan={2}>{alertNotifSetupInput.smtpServer}</td></tr>
                <tr><th>SMTP Port</th><td colSpan={2}>{alertNotifSetupInput.smtpPort}</td></tr>
                <tr><th>Password</th><td colSpan={2}>{alertNotifSetupInput.password}</td></tr>
                </tbody>

            </table>
            <div className="vspacer-20" />
            <button className="btn btn-primary" disabled={started} onClick={(e) => initiateDatabaseCreation(e)}>
                Initiate Database Creation
            </button>
        </div>
    );
}

export default SummaryComponent;