import React from "react";
import {Detail, Rule, SectionArgs} from "./Section";
import TableHeader from "./TableHeader";
import TableRow from "./TableRow";

type TableMultiProps = {
    data: { [key: string]: Detail }[][]
    columns?: string[]
    headers?: string
    args: SectionArgs
    rules?: { [key: string]: Rule; }
};

const TableMulti: React.FC<TableMultiProps> = (props) => {

    return (
        <div className={"full-width-table "}>
            <table className="table table-bordered">
                <TableHeader rules={props.rules} headers={props.headers}/>
                <tbody>
                {props.data.map((r) => {
                    return <>
                        {r.map((row, index) => {
                            return <TableRow key={index} id={index + 1} data={row} columns={props.columns}
                                             args={props.args} rules={props.rules}/>
                        })}
                    </>
                })}
                </tbody>
            </table>
        </div>
    )
}

export type {TableMultiProps};
export default TableMulti;