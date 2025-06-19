import React, { FunctionComponent, useState } from 'react';
import AlertDataSetup from "./alert-data-setup/alert-data-setup.component";
import { ILocationConfig } from "./database-setup.interfaces";
import { IAlertData } from "./alert-data-setup/alert-data-setup.interfaces";
import { IDatabaseSetupProps } from '../../setup.interfaces';
import LocationsSetupComponent from "./locations-setup/locations-setup.component";
import { IDeviceConfig } from "./device-configuration/device-configuration.interfaces";

const initial_additional_sequences_config: IAlertData = { queries: [] };
const initial_location_config: ILocationConfig = { nanoporeLocation: "" };
const initial_alert_config: IDeviceConfig = { device: "" };

const DatabaseSetupComponent: FunctionComponent<IDatabaseSetupProps> = ({ advanceStep, update }) => {
    const [alertData, setAlertData] = useState(initial_additional_sequences_config);
    const [locationConfig, setLocationConfig] = useState(initial_location_config);
    const [alertConfig, setAlertConfig] = useState(initial_alert_config);

    const updateDatabaseSetupConfiguration = () => {
        const invalidQueries = alertData.queries.filter(
            q => !q.threshold || q.threshold.trim() === "" || isNaN(parseFloat(q.threshold))
        );
        if (invalidQueries.length > 0) {
            alert("Please provide a valid threshold for all queries.");
            return;
        }
        update({ queries: alertData, locations: locationConfig, device: alertConfig });
        advanceStep();
    };

    return (
        <div className="container-fluid vspacer-100 d-flex p-0 flex-column h-100">
            <div className="vspacer-50" />
            <div className="twline"><span>NANOPORE SETUP</span></div>
            <div className="row justify-content-around">
                <LocationsSetupComponent initialConfig={initial_location_config} updateConfig={setLocationConfig} />
            </div>
            <div className="vspacer-50" />
            <div className="twline"><span>ALERT DATA SETUP</span></div>
            <AlertDataSetup initialConfig={initial_additional_sequences_config} updateConfig={setAlertData} />
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