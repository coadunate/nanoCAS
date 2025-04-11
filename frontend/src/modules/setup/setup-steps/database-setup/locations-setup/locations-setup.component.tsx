import React, {FunctionComponent, useEffect, useState} from 'react';
import {IDatabaseSetupConstituent, ILocationConfig} from "../database-setup.interfaces";
import { OverlayTrigger, Tooltip } from 'react-bootstrap';

type IKeys = "minionLocation"
const initial_location_config: ILocationConfig = {
    minionLocation: ""
}

const LocationsSetupComponent: FunctionComponent<IDatabaseSetupConstituent> = ({updateConfig}) => {
    const [locationConfig, setLocationConfig] = useState(initial_location_config);
    const [error, setError] = useState("");

    const handleDataChange = (key: IKeys) => (evt: React.ChangeEvent<HTMLInputElement>) => {
        const value = evt.target.value;
        setLocationConfig((prev) => ({...prev, [key]: value}));
        setError(value ? "" : "Nanopore directory is required.");
    };

    useEffect(() => {
        updateConfig((prevState: any) => ({
            ...prevState,
            minionLocation: locationConfig.minionLocation
        }));
    }, [locationConfig, updateConfig]);

    return (
        <div className="col-lg-5 m-0 container">
            <br/>
            <h4>Nanopore Location</h4>
            <p>Enter the directory where Nanopore data is stored.</p>
            <div className="vspacer-20"/>
            <div className="row ml-auto">
                <OverlayTrigger
                    placement="top"
                    overlay={<Tooltip id="tooltip">Path to your Nanopore data directory</Tooltip>}
                >
                    <input
                        name="minionLocationText"
                        className={`form-control ${error ? 'is-invalid' : ''}`}
                        placeholder="/path/to/minion/dropbox"
                        type="text"
                        value={locationConfig.minionLocation}
                        onChange={handleDataChange("minionLocation")}
                    />
                </OverlayTrigger>
                {error && <div className="invalid-feedback">{error}</div>}
            </div>
            <br/>
        </div>
    );
};

export default LocationsSetupComponent
