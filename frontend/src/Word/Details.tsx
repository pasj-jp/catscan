import React from "react";
import {OkType, Rule, SectionArgs} from "./Section";
import TableMulti from "./TableMulti";
import Table from "./Table";
import { useLanguage } from "../i18n";

type DetailsProps = {
    ok: OkType
    title: string
    args: SectionArgs
    details: any
    rules: { [key: string]: Rule; }
}

const Details: React.FC<DetailsProps> = (props) => {
    const { language } = useLanguage();
    const isMulti = Boolean(
        props.args.style_multi &&
        Array.isArray(props.details) &&
        props.details.length > 0 &&
        Array.isArray(props.details[0])
    );

    return (
        <details open={props.ok !== true} className="details-jacow">
            <summary className="details-summary-jacow font-weight-bold">
                <i className="fas fa-list mr-2 text-primary"></i>
                {language === 'ja' ? `${props.title} のスタイル詳細` : `Style Breakdown for ${props.title}`}
            </summary>
            {isMulti ?
                <TableMulti data={props.details} args={props.args} rules={props.rules} />
                :
                <Table data={props.details} args={props.args} rules={props.rules} />
            }
        </details>
    );
}

export default Details;