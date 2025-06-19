type IAlertData = {
    queries: IQuery[]
}

type IQuery = {
    name: string,
    file: string,
    threshold: string,
    current_fold_change: number,
    alert: boolean,
   selected_headers?: string[]
}

export type {
    IAlertData,
    IQuery
}