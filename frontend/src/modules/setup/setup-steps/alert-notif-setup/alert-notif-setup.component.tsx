import React, { FunctionComponent, useState } from 'react';
import { IAlertNotifSetupProps } from '../../setup.interfaces';
import { IAlertNotifSetupInput } from './alert-notif-setup.interfaces';

const AlertNotifSetupComponent: FunctionComponent<IAlertNotifSetupProps> = ({ advanceStep, update }) => {
    const [enableEmail, setEnableEmail] = useState(false);
    const [emailConfig, setEmailConfig] = useState({
        sender: '',
        recipient: '',
        smtpServer: '',
        smtpPort: 587,
        password: ''
    });
    const [enableSMS, setEnableSMS] = useState(false);
    const [smsRecipient, setSmsRecipient] = useState('');
    const [error, setError] = useState('');

    const handleEmailConfigChange = (key: string) => (evt: React.ChangeEvent<HTMLInputElement>) => {
        setEmailConfig((prev) => ({ ...prev, [key]: evt.target.value }));
    };

    const updateAlertNotifSetupConfiguration = () => {
        setError('');
        if (enableEmail) {
            const { sender, recipient, smtpServer, smtpPort, password } = emailConfig;
            if (!sender || !recipient || !smtpServer || !smtpPort || !password) {
                setError('All email fields are required when email notifications are enabled.');
                return;
            }
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(sender) || !emailRegex.test(recipient)) {
                setError('Invalid email format.');
                return;
            }
        }
        if (enableSMS && !smsRecipient) {
            setError('Recipient phone number is required when SMS notifications are enabled.');
            return;
        }

        const alertNotifConfig: IAlertNotifSetupInput = {
            enableEmail,
            emailConfig: enableEmail ? emailConfig : undefined,
            enableSMS,
            smsRecipient: enableSMS ? smsRecipient : undefined,
        };
        update(alertNotifConfig);
        advanceStep();
    };

    return (
        <div className="container-fluid vspacer-100 d-flex p-0 flex-column h-100" style={{ borderTop: "1px solid #CCC" }}>
            <div className="vspacer-20"></div>
            <p className="lead text-center">Set up notification preferences</p>
            <div className="vspacer-20"></div>
            <div className="container">
                {error && <div className="mx-auto col-sm-8 d-flex flex-row alert alert-danger text-left">ERROR –– {error}</div>}
                <div className="mb-3 d-flex flex-row">
                    <label className="col-sm-4 col-form-label text-right">
                        <h4>Enable Email Notifications</h4>
                    </label>
                    <div className="col-sm-4">
                        <input
                            type="checkbox"
                            checked={enableEmail}
                            onChange={(e) => setEnableEmail(e.target.checked)}
                        />
                    </div>
                </div>
                {enableEmail && (
                    <>
                        <div className="mb-3 d-flex flex-row">
                            <label className="col-sm-4 col-form-label text-right">Sender</label>
                            <div className="col-sm-4">
                                <input className="form-control" type="text" value={emailConfig.sender} onChange={handleEmailConfigChange("sender")} placeholder="sender@email.com" />
                            </div>
                        </div>
                        <div className="mb-3 d-flex flex-row">
                            <label className="col-sm-4 col-form-label text-right">Recipient</label>
                            <div className="col-sm-4">
                                <input className="form-control" type="text" value={emailConfig.recipient} onChange={handleEmailConfigChange("recipient")} placeholder="recipient@email.com" />
                            </div>
                        </div>
                        <div className="mb-3 d-flex flex-row">
                            <label className="col-sm-4 col-form-label text-right">SMTP Server</label>
                            <div className="col-sm-4">
                                <input className="form-control" type="text" value={emailConfig.smtpServer} onChange={handleEmailConfigChange("smtpServer")} placeholder="smtp.google.com" />
                            </div>
                        </div>
                        <div className="mb-3 d-flex flex-row">
                            <label className="col-sm-4 col-form-label text-right">SMTP Port</label>
                            <div className="col-sm-4">
                                <input className="form-control" type="number" value={emailConfig.smtpPort} onChange={(e) => setEmailConfig({ ...emailConfig, smtpPort: parseInt(e.target.value) })} placeholder="587" />
                            </div>
                        </div>
                        <div className="mb-3 d-flex flex-row">
                            <label className="col-sm-4 col-form-label text-right">Password</label>
                            <div className="col-sm-4">
                                <input className="form-control" type="password" value={emailConfig.password} onChange={handleEmailConfigChange("password")} placeholder="······" />
                            </div>
                        </div>
                    </>
                )}
                <div className="mb-3 d-flex flex-row">
                    <label className="col-sm-4 col-form-label text-right">
                        <h4>Enable SMS Notifications</h4>
                    </label>
                    <div className="col-sm-4">
                        <input
                            type="checkbox"
                            checked={enableSMS}
                            onChange={(e) => setEnableSMS(e.target.checked)}
                        />
                    </div>
                </div>
                {enableSMS && (
                    <div className="mb-3 d-flex flex-row">
                        <label className="col-sm-4 col-form-label text-right">Recipient Phone Number</label>
                        <div className="col-sm-4">
                            <input className="form-control" type="text" value={smsRecipient} onChange={(e) => setSmsRecipient(e.target.value)} placeholder="+1234567890" />
                        </div>
                    </div>
                )}
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