type IAdditionalSequences = {
    queries: IQuery[]
}

type IQuery = {
    name: string,
    file: string,
    threshold: string,
    current_breadth: number,
    alert: boolean
}

export type {
    IAdditionalSequences,
    IQuery
}