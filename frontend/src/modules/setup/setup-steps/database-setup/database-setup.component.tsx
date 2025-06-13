import React, { FunctionComponent, useState } from 'react';
import AdditionalSequencesSetupComponent from "./additional-sequences-setup/additional-sequences-setup.component";
import { ILocationConfig } from "./database-setup.interfaces";
import { IAdditionalSequences } from "./additional-sequences-setup/additional-sequences-setup.interfaces";
import { IDatabaseSetupProps } from '../../setup.interfaces';
import LocationsSetupComponent from "./locations-setup/locations-setup.component";
import AlertConfigurationComponent from "./alert-configuration/alert-configuration.component";
import { IAlertConfig } from "./alert-configuration/alert-configuration.interfaces";

const initial_additional_sequences_config: IAdditionalSequences = { queries: [] };
const initial_location_config: ILocationConfig = { nanoporeLocation: "" };
const initial_alert_config: IAlertConfig = { device: "" };

const DatabaseSetupComponent: FunctionComponent<IDatabaseSetupProps> = ({ advanceStep, update }) => {
    const [additionalSequences, setAdditionalSequences] = useState(initial_additional_sequences_config);
    const [locationConfig, setLocationConfig] = useState(initial_location_config);
    const [alertConfig, setAlertConfig] = useState(initial_alert_config);
    const [fileType, setFileType] = useState<'FASTQ' | 'BAM'>('FASTQ');

    const updateDatabaseSetupConfiguration = () => {
        const invalidQueries = additionalSequences.queries.filter(
            q => !q.threshold || q.threshold.trim() === "" || isNaN(parseFloat(q.threshold))
        );
        if (invalidQueries.length > 0) {
            alert("Please provide a valid threshold for all queries.");
            return;
        }
        update({ queries: additionalSequences, locations: locationConfig, device: alertConfig, fileType });
        advanceStep();
    };

    return (
        <div className="container-fluid vspacer-100 d-flex p-0 flex-column h-100" style={{ borderTop: "1px solid #CCC" }}>
            <div className="row justify-content-around">
                <AlertConfigurationComponent initialConfig={initial_alert_config} updateConfig={setAlertConfig} />
                <LocationsSetupComponent initialConfig={initial_location_config} updateConfig={setLocationConfig} />
                <div className="col-lg-5 m-0 container">
                    <br />
                    <h4>File Type</h4>
                    <p>Select the expected input file type. For BAM files, ensure they are aligned to the database sequences.</p>
                    <div className="vspacer-20" />
                    <select
                        className="form-control"
                        value={fileType}
                        onChange={(e) => setFileType(e.target.value as 'FASTQ' | 'BAM')}
                    >
                        <option value="FASTQ">FASTQ</option>
                        <option value="BAM">BAM</option>
                    </select>
                    <br />
                </div>
            </div>
            <div className="vspacer-50" />
            <div className="twline"><span>ALERT SEQUENCES</span></div>
            <AdditionalSequencesSetupComponent initialConfig={initial_additional_sequences_config} updateConfig={setAdditionalSequences} />
            <br />
            <div className="vspacer-50" />
            <hr />
            <br />
            <div className="container text-center">
                <button className="btn btn-success col-lg-2 mx-auto" onClick={updateDatabaseSetupConfiguration}>
                    Next Step
                </button>
            </div>
        </div>
    );
};

export default DatabaseSetupComponent;