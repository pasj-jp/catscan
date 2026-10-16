import React from "react";
import {Detail, SectionArgs} from "./Section";

type TableCellProps = {
    col: boolean | string,
    value: Detail,
    loop: { index: number },
    args: SectionArgs
};

const TableCell: React.FC<TableCellProps> = (props) => {
    if (typeof props.col === 'string') {
        if (props.col === 'loop.index' || props.col === 'id') {
            return <td className="text-center font-weight-bold">{props.value ?? props.loop.index}</td>;
        } else if (props.col === 'in_table' && typeof props.value === 'string') {
            return <td dangerouslySetInnerHTML={{__html: props.value}}></td>;
        } else if (props.col === 'text' && typeof props.value === 'string') {
            return (
                <td title={props.value}>
                    {props.args.truncate_text && props.value.length > props.args.truncate_text
                        ? `${props.value.substring(0, props.args.truncate_text)}...`
                        : props.value}
                </td>
            );
        } else if (props.col.indexOf("_ok") !== -1 || props.col === 'ok') {
            switch (props.value) {
                case 2:
                    return (
                        <td className="bg-warning text-white text-center">
                            <i className="fas fa-2x fa-exclamation"></i>
                        </td>
                    );
                case true:
                    return (
                        <td className="bg-success text-white text-center">
                            <i className="fas fa-2x fa-check"></i>
                        </td>
                    );
                case false:
                    return (
                        <td className="bg-danger text-white text-center">
                            <i className="fas fa-2x fa-times"></i>
                        </td>
                    );
                default:
                    return <td className="text-center text-muted">-</td>;
            }
        } else if (Array.isArray(props.value)) {
            return (
                <td>
                    <ul className="list-jacow mb-0 pl-3">
                        {props.value.map((item, idx) => (
                            <li key={idx}>{String(item)}</li>
                        ))}
                    </ul>
                </td>
            );
        } else if (typeof props.value === 'string' && props.value.indexOf('should be') !== -1) {
            return <td className="font-weight-bold bg-warning text-dark">{props.value}</td>;
        } else if (typeof props.value === 'object' && props.value !== null) {
            return <td>{JSON.stringify(props.value)}</td>;
        } else {
            return (
                <td>
                    {props.value === true && <i className="fas fa-check text-success"></i>}
                    {props.value === false && <i className="fas fa-times text-danger"></i>}
                    {typeof props.value !== 'boolean' && (props.value !== null && props.value !== undefined ? String(props.value) : <span className="text-muted">-</span>)}
                </td>
            );
        }
    }
    return <td>-</td>;
};

export default TableCell;