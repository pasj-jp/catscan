import React from "react";
import Rules from "./Rules";
import ExtraInfo from "./ExtraInfo";
import Details from "./Details";

type OkType = true | false | 2;

type ExtraInfoType = {
    columns?: string[]
    headers?: string
    title?: string,
    multi?: boolean
};

type Rule = {
    alignment: string
    bold: boolean
    font_size: number
    italic?: boolean
    space_after: number | [string | number],
    space_before: number | [string | number],
    type: string
    styles: { [key: string]: string; }
};

type Detail = boolean | string[] | number | number[] | string | null;

type SectionProps = {
    name?: string
    anchor?: string
    title?: string
    ok: OkType
    rules?: { [key: string]: Rule; }
    extra_rules?: string[] | string
    help_info?: string
    details?: { [key: string]: Detail }[]
    extra_info?: string | ExtraInfoType
    show_total?: boolean
}

type SectionArgs = {
    truncate_text?: number
    style_multi?: boolean
    section_header?: string
}

import { useLanguage } from "../i18n";

const columnHeaders: { [key: string]: string } = {
    'alignment': 'Alignment',
    'font_size': 'Font Size',
    'all_caps': 'All Caps',
    'case': 'Case',
    'bold': 'Bold',
    'italic': 'Italic',
    'space_before': 'Space Before',
    'space_after': 'Space After',
    'first_line_indent': 'First Line Indent',
    'hanging_indent': 'Hanging Indent',
};
const Section: React.FC<SectionProps> = (props) => {
    const { language } = useLanguage();
    const sectionTitle = props.title || props.name || 'Section';

    const getSectionArgs = (): SectionArgs => {
        switch (props.name) {
            case 'Paragraphs':
                return {'truncate_text': 200}
            case 'References':
                return {'truncate_text': 50}
            case 'Figures':
                return {'style_multi': true}
            case 'Abstract Submission':
                return {'section_header': 'Conformance with Abstract Submission'}
            default:
                return {}
        }
    }

    const sectionArgs = getSectionArgs();

    return (<div className={"section card shadow-sm border-0 mb-3"}>
            <div className={"card-header bg-light d-flex justify-content-between align-items-center py-3"}>
                <div className={"title-icons"}>
                    {props.ok === true && <i className={"text-success fas fa-check-circle"}></i>}
                    {props.ok === false && <i className={"text-danger fas fa-times-circle"}></i>}
                    {props.ok === 2 && <i className={"text-warning fas fa-exclamation-triangle"}></i>}
                    {(typeof sectionArgs.section_header === 'undefined') && <h5 className="font-weight-bold text-dark mb-0">{sectionTitle}</h5>}
                    {(typeof sectionArgs.section_header === 'string') &&
                        <h5 className="font-weight-bold text-dark mb-0" dangerouslySetInnerHTML={{__html: sectionArgs.section_header}}></h5>}
                </div>
                {props.help_info &&
                    <a href={`https://www.jacow.org/Authors/${props.help_info}`} target="_blank" rel="noreferrer" className="small text-secondary">
                        <i className={"fas fa-question-circle mr-1"}></i>
                        {language === 'ja' ? 'ガイド' : 'Help'}
                    </a>
                }
            </div>

            <Rules rules={props.rules || {}} extra_rules={props.extra_rules || ''} title={sectionTitle}/>
            {props.extra_info &&
                <ExtraInfo title={sectionTitle} extra_info={props.extra_info} show_total={props.show_total ?? false}
                           details={props.details || []} ok={props.ok} args={sectionArgs}/>}

            {props.rules && props.details && (props.details.length > 0) &&
                <Details ok={props.ok} args={sectionArgs} details={props.details} rules={props.rules}
                         title={sectionTitle}/>}

            {props.rules && (!props.details || props.details.length === 0) && <div>
                <div className="jacow-not-found text-muted small p-3">
                    {language === 'ja'
                        ? `${sectionTitle} は検出されませんでした。必要に応じて原稿フォーマットをご確認ください。`
                        : `No ${sectionTitle} found. Please check formatting if there should be some.`}
                </div>
            </div>}
        </div>
    );
}

export {columnHeaders};
export type {SectionProps, OkType, SectionArgs, Rule, Detail, ExtraInfoType};
export default Section;