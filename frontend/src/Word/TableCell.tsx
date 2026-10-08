import {Detail, SectionArgs} from "./Section";

type TableCellProps = {
    col: boolean | string,
    value: Detail,
    loop: { index: number },
    args: SectionArgs
};

const TableCell: React.FC<TableCellProps> = (props) => {

    if (typeof props.col === 'string') {
        if (props.col === 'loop.index') {
            return <td>{props.loop.index}</td>;
        } else if (props.col === 'in_table' && typeof props.value === 'string') {
            return <td dangerouslySetInnerHTML={{__html: props.value}}></td>
        } else if (props.col === 'text' && typeof props.value === 'string') {
            return <td title={props.value}>
                {props.args.truncate_text ? props.value.substring(0, props.args.truncate_text) : props.value}
            </td>
        } else if (props.col.indexOf("_ok") !== -1) {
            switch (props.value) {
                case 2:
                    return <td className="bg-warning text-white text-center">
                        <i className={"fas fa-2x fa-exclamation"}></i>
                    </td>;
                case true:
                    return <td className="bg-success text-white text-center">
                        <i className={"fas fa-2x fa-check"}></i>
                    </td>;
                case false:
                    return <td className="bg-danger text-white text-center">
                        <i className={"fas fa-2x fa-times"}></i>
                    </td>;
            }
        } else if (Array.isArray(props.value)) {
            return <td>
                <ul className="list-jacow">
                    {props.value.map((item) => {
                        return <li>{item}</li>
                    })}
                </ul>
            </td>
        } else if (typeof props.value === 'string' && props.value.indexOf('should be') !== -1) {
            return <td className={"font-weight-bold bg-warning"}>{props.value}</td>
        } else {
            return <td>
                {props.value === true && <i className={"fas fa-check"}></i>}
                {props.value === false && <i className={"fas fa-times"}></i>}
                {props.value ?? "None"}
            </td>
        }
    }
    return <></>;
}

export default TableCell;