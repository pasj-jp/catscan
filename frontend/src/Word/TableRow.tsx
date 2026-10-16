import {Detail, Rule, SectionArgs, getRuleAttributes} from "./Section";
import React from "react";
import TableCell from "./TableCell";

type TableRowProps = {
    id: number,
    args: SectionArgs,
    columns?: string[]
    rules?: { [key: string]: Rule; }
    data: { [key: string]: Detail}
};

const computeRowVerdict = (data: { [key: string]: Detail }): Detail => {
    if (data.ok !== undefined && data.ok !== null) {
        return data.ok;
    }
    if (data.case_ok === false || data.lang_ok === false || data.delimiter_ok === false || data.number_ok === false) {
        return false;
    }
    return data.style_ok ?? true;
};

const TableRow: React.FC<TableRowProps> = (props) => {
    const ruleAttrs = getRuleAttributes(props.rules);
    const hasRules = (ruleAttrs.length > 0 || Boolean(props.rules && Object.keys(props.rules).length > 0)) && !props.columns;

    return (
        <tr>
            {hasRules && <TableCell col="text" value={props.data.text} args={props.args} loop={{'index': props.id}} />}
            {hasRules && <TableCell col="style" value={props.data.style} args={props.args} loop={{'index': props.id}} />}
            {hasRules && ruleAttrs.map((attr, index) => (
                <TableCell key={index} col={attr} value={props.data[attr]} args={props.args} loop={{'index': props.id}} />
            ))}
            {hasRules && <TableCell col="style_ok" value={computeRowVerdict(props.data)} args={props.args} loop={{'index': props.id}} />}
            {!hasRules && props.columns && props.columns.map((col, index) => {
                let value = props.data[col];
                if (col === 'id' || col === 'loop.index') {
                    value = props.data[col] ?? props.id;
                }
                return <TableCell key={index} col={col} value={value} args={props.args} loop={{'index': props.id}} />
            })}
        </tr>
    );
};

export default TableRow;