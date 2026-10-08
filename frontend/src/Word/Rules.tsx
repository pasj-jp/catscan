import React from "react";
import {columnHeaders, Rule} from "./Section";
import { useLanguage } from "../i18n";

type RuleProps = {
    rules: { [key: string]: Rule; }
    extra_rules: string[] | string
    title: string
}

const Rules: React.FC<RuleProps> = (props) => {
    const { language } = useLanguage();

    return (
        <>{(props.rules || props.extra_rules) &&
            <details className="details-jacow">
                <summary className="details-summary-jacow">
                    {language === 'ja' ? `${props.title} の検証ルール` : `Rules for ${props.title}`}
                </summary>
                {Array.isArray(props.extra_rules) &&
                    <div className="extra-jacow-rules">
                        {props.extra_rules.map((rule) => {
                            return (<div key={rule} dangerouslySetInnerHTML={{__html: rule}}></div>)
                        })}
                    </div>
                }
                {typeof props.extra_rules === 'string' &&
                    <div className="extra-jacow-rules" dangerouslySetInnerHTML={{__html: props.extra_rules}}></div>
                }

                {props.rules &&
                    <div className={"full-width-table"}>
                        <table className="table table-sm">
                            <thead>
                            <tr>
                                <th>{language === 'ja' ? '種別' : 'Type'}</th>
                                <th>{language === 'ja' ? 'スタイル定義' : 'Details'}</th>
                                {props.rules[Object.keys(props.rules)[0]] && Object.keys(props.rules[Object.keys(props.rules)[0]]).map((rule) => {
                                    if (rule !== 'type' && rule !== 'styles') {
                                        return (<th key={rule}>{columnHeaders[rule]}</th>)
                                    }
                                    return null;
                                })}
                            </tr>
                            </thead>
                            <tbody>
                            {Object.entries(props.rules).map((rule) => {
                                const stylesDict = rule[1].styles || {};
                                const styleName = stylesDict['pasj'] || stylesDict['jacow'] || Object.values(stylesDict)[0] || 'Standard';
                                return (<tr key={rule[0]}>
                                    <td>{rule[1].type}</td>
                                    <td>'{styleName}' {language === 'ja' ? 'または同等スタイル' : 'or equivalent style'}</td>
                                    {Object.entries(rule[1]).map((r) => {
                                        return ((r[0] !== 'type' && r[0] !== 'styles') ?
                                            <td key={r[0]}>
                                                {(typeof r[1] === 'string') && r[1]}
                                                {(typeof r[1] === 'number') && r[1]}
                                                {(r[1] === null) && <>None</>}
                                                {(typeof r[1] === 'boolean') && <>{r[1] ? "Yes" : "No"}</>}
                                                {(typeof r[1] === 'object') && r[1] !== null && Object.entries(r[1]).map((a: ([string, string | number])) => {
                                                    return (<>{a[1]}</>);
                                                })}
                                            </td> : null)
                                    })}
                                </tr>)
                            })}
                            </tbody>
                        </table>
                    </div>
                }
            </details>
        }</>
    );
}

export default Rules;