import {IAlertData} from "./alert-data-setup/alert-data-setup.interfaces";
import {IDeviceConfig} from "./device-configuration/device-configuration.interfaces"
import React from "react";

type ILocationConfig = {
    nanoporeLocation: string
}

type IDatabseSetupInput = {
    queries: IAlertData,
    locations: ILocationConfig,
    device: IDeviceConfig,
}


type IDatabaseSetupConstituent<T> = {
    initialConfig: T,
    updateConfig: React.Dispatch<React.SetStateAction<T>>
}

export type {
    IDatabaseSetupConstituent,
    IDatabseSetupInput,
    ILocationConfig
}
