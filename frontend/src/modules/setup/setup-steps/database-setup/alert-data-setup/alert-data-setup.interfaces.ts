type IAlertData = {
    queries: IQuery[],
    gff_file?: string
}

type IQuery = {
    name: string,
    file: string,
    alert_on_depth: boolean,
    depth_threshold?: string,
    alert_on_breadth: boolean,
    breadth_threshold?: string,
    currrent_breadth?: number,
    current_deth?: number,
    header?: string
}

export type {
    IAlertData,
    IQuery
}