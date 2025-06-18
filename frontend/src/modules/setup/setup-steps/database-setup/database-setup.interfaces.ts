import {IAlertData} from "./alert-data-setup/alert-data-setup.interfaces";
import {IAlertConfig} from "./alert-configuration/alert-configuration.interfaces"
import React from "react";

type ILocationConfig = {
    nanoporeLocation: string
}

type IDatabseSetupInput = {
    queries: IAlertData,
    locations: ILocationConfig,
    device: IAlertConfig,
}


type IDatabaseSetupConstituent = {
    initialConfig: IAlertData | ILocationConfig | IAlertConfig,
    updateConfig: React.Dispatch<React.SetStateAction<ILocationConfig>> | React.Dispatch<React.SetStateAction<IAlertData>> | React.Dispatch<React.SetStateAction<IAlertConfig>>
}

export type {
    IDatabaseSetupConstituent,
    IDatabseSetupInput,
    ILocationConfig
}
