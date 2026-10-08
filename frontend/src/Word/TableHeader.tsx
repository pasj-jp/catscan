import React from "react";
import {Rule} from "./Section";
import {useLanguage} from "../i18n";

type TableHeadersProps = {
    headers?: string
    rules?: { [key: string]: Rule; }
};

const sentenceCase = (str: string) => {
    if ((str === null) || (str === ''))
        return '';
    else
        str = str.toString();

    return str.replace(/\w\S*/g,
        function (txt) {
            return txt.charAt(0).toUpperCase() +
                txt.substring(1).toLowerCase();
        });
}

const TableHeader: React.FC<TableHeadersProps> = (props) => {
    const { language } = useLanguage();
    const firstRule = props.rules && Object.entries(props.rules)[0][1];
    return (<>
        {firstRule &&
            <thead>
            <tr>
                <th rowSpan={2}>{language === 'ja' ? '本文テキスト' : 'Text'}</th>
                <th colSpan={9}>{language === 'ja' ? 'スタイル検査項目' : 'Style Attributes'}</th>
            </tr>
            <tr>
                <th>{language === 'ja' ? 'スタイル名' : 'Text Style Name'}</th>
                {Object.keys(firstRule).map((rule) => {
                    return ['type', 'styles'].indexOf(rule) === -1 ? <th key={rule}>{sentenceCase(rule.replace("_", " "))}</th> : null;
                })}
                <th>{language === 'ja' ? '判定' : 'Ok'}</th>
            </tr>
            </thead>
        }
        {(typeof props.headers === 'string') && <thead dangerouslySetInnerHTML={{__html: props.headers}}></thead>}
    </>);
}

export default TableHeader;