type IAdditionalSequences = {
    queries: IQuery[]
}

type IQuery = {
    name: string,
    file: string,
    threshold: string,
    current_fold_change: number,
    alert: boolean,
    header: string,
}

export type {
    IAdditionalSequences,
    IQuery
}