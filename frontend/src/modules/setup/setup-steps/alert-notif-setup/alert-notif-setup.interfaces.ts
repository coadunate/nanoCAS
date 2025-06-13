type IAlertNotifSetupInput = {
    enableEmail: boolean,
    emailConfig?: {
        sender: string,
        recipient: string,
        smtpServer: string,
        smtpPort: number,
        password: string,
    },
    enableSMS: boolean,
    smsRecipient?: string,
}

export type {
    IAlertNotifSetupInput
}