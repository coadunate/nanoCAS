import React, { useRef, useLayoutEffect, useState } from 'react';
import { Tooltip, OverlayTrigger, Form } from 'react-bootstrap';

interface Alignment {
    start: number;
    end: number;
    strand: string;
}

interface Region {
    start: number;
    end: number;
    id: string;
    read_count: number;
}

interface AlignmentViewerProps {
    refId: string;
    refLength: number;
    alignments: Alignment[];
    regions: Region[];
}

const AlignmentViewer: React.FC<AlignmentViewerProps> = ({ refId, refLength, alignments, regions }) => {
    const containerRef = useRef<HTMLDivElement>(null);
    const [svgWidth, setSvgWidth] = useState(800);
    const [showRegions, setShowRegions] = useState(true);

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

    // Layout constants
    const topMargin = 50;
    const bottomMargin = 30;
    const leftMargin = 60;
    const rightMargin = 40;
    const queryBarHeight = 25;
    const readHeight = 15;
    const rowGap = 8;
    const noReadsPlaceholderHeight = 25;

    // Stacking algorithm for reads
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
    const xAxisYPosition = topMargin + contentHeight + rowGap;
    const svgHeight = xAxisYPosition + bottomMargin;

    const sequenceXStart = leftMargin;
    const sequenceWidth = svgWidth - leftMargin - rightMargin;
    const scale = sequenceWidth / refLength;

    // X-axis tick positions
    const tickPositions = [0, Math.floor(refLength / 4), Math.floor(refLength / 2), Math.floor(3 * refLength / 4), refLength];

    return (
        <div ref={containerRef} style={{ width: '100%' }}>
            <div className="mb-3 p-2 bg-light rounded shadow-sm d-flex align-items-center gap-3 border" style={{ maxWidth: 420 }}>
                <Form>
                    <Form.Check
                        type="switch"
                        id="show-regions-switch"
                        label={
                            <span className="fw-medium">
                                Toggle GFF Regions
                            </span>
                        }
                        checked={showRegions}
                        onChange={() => setShowRegions(!showRegions)}
                        aria-label="Toggle Regions of Interest"
                        className="d-flex align-items-center"
                        style={{ minHeight: 32 }}
                    />
                </Form>
            </div>
            <svg width="100%" height={svgHeight} viewBox={`0 0 ${svgWidth} ${svgHeight}`}>
                {/* Background */}
                <rect x={0} y={0} width={svgWidth} height={svgHeight} fill="#FFF" />

                {/* Query bar */}
                <rect x={sequenceXStart} y={topMargin} width={sequenceWidth} height={queryBarHeight} fill="#ccc" stroke="#000" strokeWidth={2} />
                <polygon points={`${sequenceXStart + sequenceWidth - 10},${topMargin + 5} ${sequenceXStart + sequenceWidth},${topMargin + queryBarHeight / 2} ${sequenceXStart + sequenceWidth - 10},${topMargin + queryBarHeight - 5}`} fill="#000" />
                <polygon points={`${sequenceXStart + 10},${topMargin + 5} ${sequenceXStart},${topMargin + queryBarHeight / 2} ${sequenceXStart + 10},${topMargin + queryBarHeight - 5}`} fill="#000" />

                {/* Regions of Interest */}
                {showRegions && regions.map((region, index) => {
                    const x = sequenceXStart + region.start * scale;
                    const width = (region.end - region.start) * scale;
                    return (
                        <OverlayTrigger
                            placement="top"
                            overlay={<Tooltip id="region-tooltip">{region.id}</Tooltip>}
                            >
                                <g key={index}>
                                    <rect
                                        x={x}
                                        y={topMargin}
                                        width={width}
                                        height={queryBarHeight}
                                        fill="rgba(0, 255, 0, 0.3)"
                                        stroke="#000"
                                        strokeWidth={1}
                                        data-tip={`Gene ID: ${region.id}<br>Start: ${region.start}<br>End: ${region.end}<br>Read Count: ${region.read_count}`}
                                        data-for="region-tooltip"
                                    />
                                </g>
                        </OverlayTrigger>
                    );
                })}


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
                            fontFamily="Arial, sans-serif"
                        >
                            No Aligned Reads
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
                            <text x={x} y={xAxisYPosition + 15} textAnchor="middle" fontSize={10} fontFamily="Arial, sans-serif">
                                {pos.toLocaleString()}
                            </text>
                        </g>
                    );
                })}

                {/* Y-axis labels */}
                <text
                    x={sequenceXStart + sequenceWidth / 2}
                    y={topMargin - 10}
                    fontSize={12}
                    dominantBaseline="middle"
                    textAnchor="middle"
                    fontWeight="bold"
                    fontFamily="Arial, sans-serif"
                    style={{ textTransform: 'uppercase' }}
                >
                   {refId}
                </text>
                {rows.length > 0 && (
                    <text
                        x={leftMargin - 25}
                        y={topMargin + queryBarHeight + rowGap + readAreaHeight / 2}
                        fontSize={12}
                        dominantBaseline="middle"
                        textAnchor="middle"
                        fontFamily="Arial, sans-serif"
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