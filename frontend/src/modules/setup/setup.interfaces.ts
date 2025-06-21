import React, {FunctionComponent} from "react";
import {IDatabseSetupInput} from './setup-steps/database-setup/database-setup.interfaces';
import {IAlertNotifSetupInput} from './setup-steps/alert-notif-setup/alert-notif-setup.interfaces'
import {IDeviceConfig} from "./setup-steps/database-setup/device-configuration/device-configuration.interfaces";

type IDeviceConfigSetupProps = {
    advanceStep: () => void,
    update: React.Dispatch<React.SetStateAction<IDeviceConfig>>,
}

type IDatabaseSetupProps = {
    advanceStep: () => void,
    update: React.Dispatch<React.SetStateAction<IDatabseSetupInput>>,

}

type IAlertNotifSetupProps = {
    advanceStep: () => void,
    update: React.Dispatch<React.SetStateAction<IAlertNotifSetupInput>>,
}

type ISteps = {
    name: string,
    component: React.ReactElement<IDatabaseSetupProps> | React.ReactElement<IDeviceConfigSetupProps>
}

export type {
    IDatabaseSetupProps,
    IDeviceConfigSetupProps,
    IAlertNotifSetupProps,
    ISteps
}

