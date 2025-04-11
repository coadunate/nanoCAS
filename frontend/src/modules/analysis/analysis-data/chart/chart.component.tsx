import React, { FunctionComponent } from 'react';
import { Chart } from "react-google-charts";

type IChartData = {
    queries_data: any
}

const ChartComponent: FunctionComponent<IChartData> = ({ queries_data }) => {
    return (
        <div>
            <Chart
                height={"300px"}
                chartType="BarChart"
                loader={<div>Loading Chart</div>}
                data={queries_data}
                options={{
                    chartArea: { width: "50%" },
                    hAxis: { title: "Percentage (%)", minValue: 0, maxValue: 100 },
                    vAxis: { title: "Alert Sequences" },
                    bars: 'horizontal',
                    series: {
                        0: { color: '#1b9e77' }, // Match Percentage
                        1: { color: '#d95f02' }  // Threshold
                    }
                }}
            />
        </div>
    );
};

export default React.memo(
    ChartComponent,
    (prevProps, nextProps) => JSON.stringify(prevProps.queries_data) === JSON.stringify(nextProps.queries_data)
);