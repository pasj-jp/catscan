import React from 'react';
import {Detail, ExtraInfoType, OkType, SectionArgs} from "./Section";
import Table from "./Table";
import TableMulti from "./TableMulti";

type ExtraInfoProps = {
    extra_info: string | ExtraInfoType
    title: string
    show_total: boolean
    details: any
    ok: OkType,
    args: SectionArgs
}

const ExtraInfo: React.FC<ExtraInfoProps> = (props) => {
    const isMulti = (props.extra_info && typeof props.extra_info !== 'string' && props.extra_info.multi) || false;
    return <>
        {props.extra_info && typeof props.extra_info === 'string' &&
            <div className="extra-jacow-info" dangerouslySetInnerHTML={{__html: props.extra_info}}></div>}

        {props.extra_info && typeof props.extra_info !== 'string' && props.extra_info.title && (!props.show_total || props.details.length > 0) &&
            <details open={props.ok !== true} className={`details-jacow`}>
                <summary className="details-summary-jacow">{props.extra_info.title} for {props.title}</summary>
                {isMulti ?
                    <div className={"mt-3"}><TableMulti data={props.details} columns={props.extra_info.columns}
                                                        args={props.args} headers={props.extra_info.headers}/></div>
                    :
                    <div className={"mt-3"}><Table data={props.details} columns={props.extra_info.columns}
                                                   args={props.args} headers={props.extra_info.headers}/></div>
                }
            </details>
        }
    </>
}


export default ExtraInfo;