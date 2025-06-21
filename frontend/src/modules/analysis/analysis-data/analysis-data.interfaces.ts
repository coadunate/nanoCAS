import { IQuery } from "../../setup/setup-steps/database-setup/alert-data-setup/alert-data-setup.interfaces";

type IAnalysisData = {
    "status": number,
    "data": {
        "minion": string,
        "queries": IQuery[],
        "projectId": string,
        "device": string
    }
}

type IAnalysisDataProps = {
    data: IAnalysisData
}

export type {
    IAnalysisData,
    IAnalysisDataProps
}