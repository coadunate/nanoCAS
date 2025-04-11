import React, {FunctionComponent, useEffect, useState} from "react";
import axios from "axios";
import {IDatabaseSetupConstituent} from "../database-setup.interfaces";
const AlertConfigurationComponent: FunctionComponent<IDatabaseSetupConstituent> = ({updateConfig}) => {
    const [devices, setDevices] = useState<string[]>([]);
    const [loaded, setLoaded] = useState(false);
    const [selectedDevice, setSelectedDevice] = useState("");

    useEffect(() => {
        (async () => {
            const res = await get_devices();
            setDevices(res.data);
            setLoaded(true);
        })();
    }, []);

    useEffect(() => {
        updateConfig((prevState: any) => ({
            ...prevState,
            device: selectedDevice
        }));
    }, [selectedDevice, updateConfig]);

    const get_devices = () => {
        return axios({
            method: 'GET',
            url: 'http://localhost:5007/index_devices'
        });
    };

    return loaded ? (
        <div className="col-lg-5 m-0 container">
            <br/>
            <h4>Device Selection</h4>
            <p>Select a device or choose to run without one.</p>
            <div className="vspacer-20"/>
            <div className="row ml-auto">
                <select
                    className="form-control"
                    onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setSelectedDevice(e.target.value)}
                    value={selectedDevice}
                >
                    <option value="">Run without device</option>
                    {devices.map((device: string) => (
                        <option key={device} value={device}>{device}</option>
                    ))}
                </select>
            </div>
            <br/>
        </div>
    ) : (
        <div className="text-muted"><i className="fa fa-spinner fa-spin"/> Searching For Devices...</div>
    );
};

export default AlertConfigurationComponent;
