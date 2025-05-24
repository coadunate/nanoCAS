import React, { FunctionComponent, useState } from 'react';
import { IAlertConfigSetupProps, IAlertNotifSetupProps, IDatabaseSetupProps } from '../../setup.interfaces';
import { IAlertNotifSetupInput } from './alert-notif-setup.interfaces';

const AlertNotifSetupComponent: FunctionComponent<IAlertNotifSetupProps> = ({ advanceStep, update }) => {

    type IKeys = "sender" | "recipient" | "smtpServer" | "smtpPort" | "password"

    const initial_alert_notif_setup_config : IAlertNotifSetupInput = {
        sender: '',
        recipient: '',
        smtpServer: '',
        smtpPort: 587,
        password: ''
    }


    const [alertNotifConfig, setAlertNotifConfig] = useState(initial_alert_notif_setup_config)
    const [error, setError] = useState('');

    const handleDataChange = (key : IKeys) => (evt: React.ChangeEvent<HTMLInputElement>) => {
        const value = evt.target.value;
        setAlertNotifConfig((prev) => ({...prev, [key]: value}));
    }

    // Validate and update configuration
    const updateAlertNotifSetupConfiguration = () => {

        // validate the input fields
        const { sender, recipient, smtpServer, smtpPort, password } = alertNotifConfig;
        if (!sender || !recipient || !smtpServer || !smtpPort || !password) {
            setError('All fields are required.');
            return;
        }
        setError(''); // Clear error if all fields are valid

        // Check if the email format is valid
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(sender) || !emailRegex.test(recipient)) {
            setError('Please provide valid sender and recipient email addresses.');
            return;
        }

        // Check if the SMTP server and port are valid
        const smtpServerRegex = /^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
        if (!smtpServerRegex.test(smtpServer)) {
            setError('Please provide a valid SMTP server address.');
            return;
        }
        // Check if the SMTP port is a valid number
        if (isNaN(smtpPort) || smtpPort <= 0 || smtpPort > 65535) {
            setError('Please provide a valid SMTP port number.');
            return;
        }
    
        // Pass email configuration to parent component via update prop
        update(alertNotifConfig);
        advanceStep();
    };

    return (
        <div className="container-fluid vspacer-100 d-flex p-0 flex-column h-100" style={{ borderTop: "1px solid #CCC" }}>
            <div className="vspacer-20"></div>
            <p className="lead text-center">We will set up an email address for alerting system</p>
            <div className="vspacer-20"></div>
            <div className="container">
                {error && <div className="mx-auto col-sm-8 d-flex flex-row alert alert-danger text-left">ERROR –– {error}</div>}
                <div className="mb-3 d-flex flex-row">
                    <label className="col-sm-4 col-form-label text-right">
                        <h4>Sender</h4>
                    </label>
                    <div className="col-sm-4">
                        <input className="form-control"
                        type="text"
                        name="sender"
                        onChange={handleDataChange("sender")}
                        value={alertNotifConfig.sender} placeholder="sender@email.com" />
                    </div>
                </div>
                <div className="mb-3 d-flex flex-row">
                    <label className="col-sm-4 col-form-label text-right">
                        <h4>Recipient</h4>
                    </label>
                    <div className="col-sm-4">
                        <input className="form-control"
                        type="text"
                        name="recipient"
                        onChange={handleDataChange("recipient")}
                        value={alertNotifConfig.recipient} placeholder="recipient@email.com" />
                    </div>
                </div>
                <div className="mb-3 d-flex flex-row">
                    <label className="col-sm-4 col-form-label text-right">
                        <h4>SMTP Server</h4>
                    </label>
                    <div className="col-sm-4">
                        <input className="form-control"
                        type="text"
                        name="smtpServer"
                        onChange={handleDataChange("smtpServer")}
                        value={alertNotifConfig.smtpServer} placeholder="smtp.google.com" />
                    </div>
                </div>
                <div className="mb-3 d-flex flex-row">
                    <label className="col-sm-4 col-form-label text-right">
                        <h4>SMTP Port</h4>
                    </label>
                    <div className="col-sm-4">
                        <input className="form-control"
                        type="text"
                        name="smtpPort"
                        onChange={handleDataChange("smtpPort")}
                        value={alertNotifConfig.smtpPort} placeholder="587" />
                    </div>
                </div>
                <div className="mb-3 d-flex flex-row">
                    <label className="col-sm-4 col-form-label text-right">
                        <h4>Password</h4>
                    </label>
                    <div className="col-sm-4">
                        <input className="form-control"
                        name="password"
                        onChange={handleDataChange("password")}
                        value={alertNotifConfig.password} 
                         type="password" placeholder="······" />
                    </div>
                </div>
            </div>
            <div className="vspacer-50" />
            <hr />
            <br />
            <div className="container text-center">
                <button className="btn btn-success col-lg-2 mx-auto" onClick={updateAlertNotifSetupConfiguration}>
                    Next Step
                </button>
            </div>
        </div>
    );
};

export default AlertNotifSetupComponent;