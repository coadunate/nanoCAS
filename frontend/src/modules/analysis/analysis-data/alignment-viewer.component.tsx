import React, { useRef, useLayoutEffect, useState } from 'react';

interface Alignment {
    start: number;
    end: number;
    strand: string;
}

interface AlignmentViewerProps {
    refLength: number;
    alignments: Alignment[];
}

const AlignmentViewer: React.FC<AlignmentViewerProps> = ({ refLength, alignments }) => {
    const containerRef = useRef<HTMLDivElement>(null);
    const [svgWidth, setSvgWidth] = useState(800);

    useLayoutEffect(() => {
        if (containerRef.current) {
            setSvgWidth(containerRef.current.offsetWidth);
        }
        const handleResize = () => {
            if (containerRef.current) {
                setSvgWidth(containerRef.current.offsetWidth);
            }
        };
        window.addEventListener('resize', handleResize);
        return () => window.removeEventListener('resize', handleResize);
    }, []);

    // Layout constants for a larger, clearer design
    const topMargin = 30;       // Increased to place "Query Sequence" label above the bar
    const bottomMargin = 30;    // Reduced to make the visualization shorter
    const leftMargin = 60;      // Increased to provide space for "Aligned Reads" label
    const rightMargin = 40;     // Added to ensure scale labels are fully visible
    const queryBarHeight = 25;
    const readHeight = 15;
    const rowGap = 8;          // Reduced to make the visualization shorter
    const noReadsPlaceholderHeight = 25; // Height for "No aligned reads" message

    // Stacking algorithm to place reads in rows without overlap
    const rows: Alignment[][] = [];
    alignments.sort((a, b) => a.start - b.start);
    alignments.forEach(alignment => {
        let placed = false;
        for (const row of rows) {
            const lastAlignment = row[row.length - 1];
            if (lastAlignment.end < alignment.start) {
                row.push(alignment);
                placed = true;
                break;
            }
        }
        if (!placed) {
            rows.push([alignment]);
        }
    });

    // Calculate heights
    const readAreaHeight = rows.length > 0
        ? rows.length * readHeight + (rows.length - 1) * rowGap
        : noReadsPlaceholderHeight;
    const contentHeight = queryBarHeight + (readAreaHeight > 0 ? rowGap + readAreaHeight : 0);
    const xAxisYPosition = topMargin + contentHeight + rowGap; // Position x-axis below content
    const svgHeight = xAxisYPosition + bottomMargin;

    const sequenceXStart = leftMargin;
    const sequenceWidth = svgWidth - leftMargin - rightMargin;
    const scale = sequenceWidth / refLength;

    // X-axis tick positions
    const tickPositions = [0, Math.floor(refLength / 4), Math.floor(refLength / 2), Math.floor(3 * refLength / 4), refLength];

    return (
        <div ref={containerRef} style={{ width: '100%' }}>
            <svg width="100%" height={svgHeight} viewBox={`0 0 ${svgWidth} ${svgHeight}`}>
                {/* Background */}
                <rect x={0} y={0} width={svgWidth} height={svgHeight} fill="#FFF" />

                {/* Query bar */}
                <rect x={sequenceXStart} y={topMargin} width={sequenceWidth} height={queryBarHeight} fill="#ccc" stroke="#000" strokeWidth={2} />
                {/* Arrowheads for query sequence */}
                <polygon points={`${sequenceXStart + sequenceWidth - 10},${topMargin + 5} ${sequenceXStart + sequenceWidth},${topMargin + queryBarHeight / 2} ${sequenceXStart + sequenceWidth - 10},${topMargin + queryBarHeight - 5}`} fill="#000" />
                <polygon points={`${sequenceXStart + 10},${topMargin + 5} ${sequenceXStart},${topMargin + queryBarHeight / 2} ${sequenceXStart + 10},${topMargin + queryBarHeight - 5}`} fill="#000" />

                {/* Reads or "No aligned reads" message */}
                {rows.length === 0 ? (
                    <g>
                        <rect
                            x={sequenceXStart}
                            y={topMargin + queryBarHeight + rowGap}
                            width={sequenceWidth}
                            height={noReadsPlaceholderHeight}
                            fill="#f5f5f5"
                            stroke="#bbb"
                            strokeDasharray="4 2"
                        />
                        <text
                            x={sequenceXStart + sequenceWidth / 2}
                            y={topMargin + queryBarHeight + rowGap + noReadsPlaceholderHeight / 2}
                            textAnchor="middle"
                            dominantBaseline="middle"
                            fontSize={15}
                            fill="#888"
                            fontStyle="italic"
                        >
                            No aligned reads
                        </text>
                    </g>
                ) : (
                    rows.map((row, rowIndex) =>
                        row.map((alignment, alignIndex) => {
                            const x = sequenceXStart + alignment.start * scale;
                            const width = (alignment.end - alignment.start) * scale;
                            const y = topMargin + queryBarHeight + rowGap + rowIndex * (readHeight + rowGap);
                            return (
                                <g key={`${rowIndex}-${alignIndex}`}>
                                    <rect
                                        x={x}
                                        y={y}
                                        width={width}
                                        height={readHeight}
                                        fill={alignment.strand === '+' ? '#00B0BD' : '#FF6A45'}
                                        stroke="#000"
                                        strokeWidth={1}
                                    />
                                    {/* Arrowheads for strand direction */}
                                    {alignment.strand === '+' ? (
                                        <polygon
                                            points={`${x + width - 5},${y + 2} ${x + width},${y + readHeight / 2} ${x + width - 5},${y + readHeight - 2}`}
                                            fill="#000"
                                        />
                                    ) : (
                                        <polygon
                                            points={`${x + 5},${y + 2} ${x},${y + readHeight / 2} ${x + 5},${y + readHeight - 2}`}
                                            fill="#000"
                                        />
                                    )}
                                </g>
                            );
                        })
                    )
                )}

                {/* X-axis */}
                <line x1={sequenceXStart} y1={xAxisYPosition} x2={sequenceXStart + sequenceWidth} y2={xAxisYPosition} stroke="#000" strokeWidth={1} />
                {tickPositions.map((pos, index) => {
                    const x = sequenceXStart + (pos * scale);
                    return (
                        <g key={index}>
                            <line x1={x} y1={xAxisYPosition} x2={x} y2={xAxisYPosition + 5} stroke="#000" strokeWidth={1} />
                            <text x={x} y={xAxisYPosition + 15} textAnchor="middle" fontSize={10}>
                                {pos.toLocaleString()}
                            </text>
                        </g>
                    );
                })}

                {/* Y-axis labels */}
                <text
                    x={svgWidth / 2}
                    y={topMargin - 10} // Positioned above the query bar
                    fontSize={12}
                    dominantBaseline="middle"
                    textAnchor="middle"
                    fontWeight="bold"
                    style={{ textTransform: 'uppercase' }}
                >
                    QUERY SEQUENCE
                </text>
                {rows.length > 0 && (
                    <text
                        x={leftMargin - 25} // Move further left to accommodate rotation
                        y={topMargin + queryBarHeight + rowGap + readAreaHeight / 2}
                        fontSize={12}
                        dominantBaseline="middle"
                        textAnchor="middle"
                        transform={`rotate(-90, ${leftMargin - 25}, ${topMargin + queryBarHeight + rowGap + readAreaHeight / 2})`}
                    >
                        Aligned Reads
                    </text>
                )}
            </svg>
        </div>
    );
};

export default AlignmentViewer;