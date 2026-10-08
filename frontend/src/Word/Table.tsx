import React from "react";
import {Detail, Rule, SectionArgs} from "./Section";
import TableHeader from "./TableHeader";
import TableRow from "./TableRow";

type TableProps = {
    data: { [key: string]: Detail}[]
    headers?: string
    args: SectionArgs,
    columns?: string[]
    rules?: { [key: string]: Rule; }
};

const Table: React.FC<TableProps> = (props) => {
    return (
        <div className={"full-width-table"}>
        <table className="table table-bordered">
            <TableHeader rules={props.rules} headers={props.headers} />
            <tbody>
            {props.data.map((row, index) => {
                return <TableRow key={index} id={index + 1} data={row} columns={props.columns} args={props.args} rules={props.rules}/>
            })}
            </tbody>
        </table>
        </div>
    )
}

export type {TableProps};
export default Table;