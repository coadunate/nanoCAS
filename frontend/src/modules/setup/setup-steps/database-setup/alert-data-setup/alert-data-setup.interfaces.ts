type IAlertData = {
    queries: IQuery[],
    gff_file?: string
}

type IQuery = {
    name: string,
    file: string,
    threshold: string,
    current_fold_change: number,
    alert: boolean,
    header?: string
}

export type {
    IAlertData,
    IQuery
}