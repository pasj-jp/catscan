import React from "react";
import { getColumnHeader, Rule } from "./Section";
import { useLanguage } from "../i18n";

type RuleProps = {
    rules?: { [key: string]: Rule; };
    extra_rules?: string[] | string;
    title: string;
};

const Rules: React.FC<RuleProps> = (props) => {
    const { language } = useLanguage();

    const hasRules = Boolean(props.rules && Object.keys(props.rules).length > 0);
    const hasExtraRules = Array.isArray(props.extra_rules)
        ? props.extra_rules.length > 0
        : Boolean(props.extra_rules && typeof props.extra_rules === 'string' && props.extra_rules.trim().length > 0);

    // If neither rules table nor extra guidelines exist, do not render empty accordion
    if (!hasRules && !hasExtraRules) {
        return null;
    }

    // Collect all unique attribute columns across all rules
    const attrKeys: string[] = [];
    if (hasRules && props.rules) {
        Object.values(props.rules).forEach((ruleObj) => {
            Object.keys(ruleObj).forEach((k) => {
                if (k !== 'type' && k !== 'styles' && !attrKeys.includes(k)) {
                    attrKeys.push(k);
                }
            });
        });
    }

    return (
        <details className="details-jacow">
            <summary className="details-summary-jacow font-weight-bold">
                <i className="fas fa-book-open mr-2 text-primary"></i>
                {language === 'ja' ? `${props.title} の検証ルール・書式基準` : `Rules & Guidelines for ${props.title}`}
            </summary>

            <div className="p-3 bg-white">
                {Array.isArray(props.extra_rules) && (
                    <div className="extra-jacow-rules mb-3">
                        <ul className="mb-0 pl-3">
                            {props.extra_rules.map((rule, idx) => (
                                <li key={idx} className="small text-secondary mb-1" dangerouslySetInnerHTML={{ __html: rule }}></li>
                            ))}
                        </ul>
                    </div>
                )}
                {typeof props.extra_rules === 'string' && props.extra_rules.trim().length > 0 && (
                    <div className="extra-jacow-rules mb-3 small text-secondary" dangerouslySetInnerHTML={{ __html: props.extra_rules }}></div>
                )}

                {hasRules && props.rules && (
                    <div className="table-responsive">
                        <table className="table table-sm table-bordered table-hover mb-0">
                            <thead className="thead-light">
                                <tr>
                                    <th style={{ minWidth: '150px' }}>{language === 'ja' ? '種別 (Type)' : 'Type'}</th>
                                    <th style={{ minWidth: '220px' }}>{language === 'ja' ? 'スタイル定義 (Style Definition)' : 'Style Definition'}</th>
                                    {attrKeys.map((attr) => (
                                        <th key={attr}>{getColumnHeader(attr, language)}</th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody>
                                {Object.entries(props.rules).map(([ruleKey, ruleVal]) => {
                                    const stylesDict = ruleVal.styles || {};
                                    const styleName = stylesDict['pasj'] || stylesDict['jacow'] || Object.values(stylesDict)[0] || 'Standard';
                                    return (
                                        <tr key={ruleKey}>
                                            <td><strong className="text-dark">{ruleVal.type || ruleKey}</strong></td>
                                            <td>
                                                <code className="text-primary font-weight-bold">{styleName}</code>
                                                <span className="text-muted small ml-1">
                                                    {language === 'ja' ? '(または同等スタイル)' : '(or equivalent)'}
                                                </span>
                                            </td>
                                            {attrKeys.map((attr) => {
                                                const attrVal = (ruleVal as any)[attr];
                                                return (
                                                    <td key={attr} className="small">
                                                        {typeof attrVal === 'string' && attrVal}
                                                        {typeof attrVal === 'number' && attrVal}
                                                        {attrVal === null || attrVal === undefined ? (
                                                            <span className="text-muted">-</span>
                                                        ) : null}
                                                        {typeof attrVal === 'boolean' && (attrVal ? "Yes" : "No")}
                                                        {typeof attrVal === 'object' && attrVal !== null && !Array.isArray(attrVal) && (
                                                            <span>{JSON.stringify(attrVal)}</span>
                                                        )}
                                                        {Array.isArray(attrVal) && (
                                                            <span>{attrVal.join(', ')}</span>
                                                        )}
                                                    </td>
                                                );
                                            })}
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </details>
    );
};

export default Rules;