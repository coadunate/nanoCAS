import {IAdditionalSequences} from "./additional-sequences-setup/additional-sequences-setup.interfaces";
import {IAlertConfig} from "./alert-configuration/alert-configuration.interfaces"
import React from "react";

type ILocationConfig = {
    minionLocation: string
}

type IDatabseSetupInput = {
    queries: IAdditionalSequences,
    locations: ILocationConfig,
    device: IAlertConfig,
    fileType: 'FASTQ' | 'BAM'
}

type IDatabaseSetupConstituent = {
    initialConfig: IAdditionalSequences | ILocationConfig | IAlertConfig,
    updateConfig: React.Dispatch<React.SetStateAction<ILocationConfig>> | React.Dispatch<React.SetStateAction<IAdditionalSequences>> | React.Dispatch<React.SetStateAction<IAlertConfig>>
}

export type {
    IDatabaseSetupConstituent,
    IDatabseSetupInput,
    ILocationConfig
}
