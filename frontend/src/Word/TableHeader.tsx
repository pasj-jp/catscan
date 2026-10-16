import React from "react";
import {Rule, getColumnHeader, getRuleAttributes} from "./Section";
import {useLanguage} from "../i18n";

type TableHeadersProps = {
    headers?: string
    rules?: { [key: string]: Rule; }
};

const TableHeader: React.FC<TableHeadersProps> = (props) => {
    const { language } = useLanguage();
    const ruleAttrs = getRuleAttributes(props.rules);
    const hasRules = ruleAttrs.length > 0 || Boolean(props.rules && Object.keys(props.rules).length > 0);

    return (<>
        {hasRules && !props.headers &&
            <thead className="thead-light">
            <tr>
                <th rowSpan={2} className="align-middle">{language === 'ja' ? '対象テキスト (Text)' : 'Text'}</th>
                <th colSpan={ruleAttrs.length + 2} className="text-center">{language === 'ja' ? 'スタイル・フォント属性検査 (Style Attributes)' : 'Style Attributes'}</th>
            </tr>
            <tr>
                <th>{language === 'ja' ? '設定スタイル名 (Style Name)' : 'Text Style Name'}</th>
                {ruleAttrs.map((rule) => {
                    return <th key={rule}>{getColumnHeader(rule, language)}</th>;
                })}
                <th className="text-center" style={{ width: '90px' }}>{language === 'ja' ? '判定' : 'Ok'}</th>
            </tr>
            </thead>
        }
        {(typeof props.headers === 'string') && <thead className="thead-light" dangerouslySetInnerHTML={{__html: props.headers}}></thead>}
    </>);
}

export default TableHeader;