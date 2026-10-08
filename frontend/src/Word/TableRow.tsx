import {Detail, Rule, SectionArgs} from "./Section";
import React from "react";
import TableCell from "./TableCell";

type TableRowProps = {
    id: number,
    args: SectionArgs,
    columns?: string[]
    rules?: { [key: string]: Rule; }
    data: { [key: string]: Detail}
};

const TableRow: React.FC<TableRowProps> = (props) => {
    const firstRule = props.rules && Object.entries(props.rules)[0][1];
    return (
        <tr>
            {firstRule && <TableCell col="text" value={props.data.text} args={props.args} loop={{'index': props.id}} />}
            {firstRule && <TableCell col="style" value={props.data.style} args={props.args} loop={{'index': props.id}} />}
            {firstRule && Object.entries(firstRule).map((rule, index) => {
                if (['type', 'styles'].indexOf(rule[0]) === -1) {
                    return <TableCell key={index} col={rule[0]} value={props.data[rule[0]]} args={props.args} loop={{'index': props.id}} />
                }
                return null
            })}
            {firstRule && <TableCell col="style_ok" value={props.data.style_ok} args={props.args} loop={{'index': props.id}} />}
            {!firstRule && props.columns && props.columns.map((col, index) => {
                let value = props.data[col];
                if (col === 'id') {
                    value = props.id;
                }
                return <TableCell key={index} col={col} value={value} args={props.args} loop={{'index': props.id}} />
            })}
        </tr>
    )
}

export default TableRow;