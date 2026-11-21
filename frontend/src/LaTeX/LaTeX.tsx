import React from "react";
import './Report.css';
import { useLanguage } from "../i18n";

interface SourceLocation {
    file?: string | null;
    line?: number | null;
}

interface StructuredIssue extends SourceLocation {
    name: string;
    category?: string;
    message: string;
    message_ja?: string;
}

interface CoverageNotice extends SourceLocation {
    message: string;
    message_ja?: string;
}

type LaTeXReport = {
    filename: string,
    report_type: "latex",
    detected_template: string,
    report_id?: string,
    total_references?: number,
    issues: StructuredIssue[],
    coverage_notices: CoverageNotice[],
};

type ReportProps = {
    report: LaTeXReport,
    onReset?: () => void,
};

const categories: Record<string, [string, string]> = {
    documentclass: ['Document Class', '文書クラス'],
    jtitle: ['Title', '題名'],
    title: ['Title', '題名'],
    jauthor: ['Authors', '著者名'],
    author: ['Authors', '著者名'],
    abstract: ['Abstract', '英文要旨'],
    body: ['Body Text', '本文'],
    figure: ['Figure Caption', '図キャプション'],
    table: ['Table Title', '表タイトル'],
    reference: ['Reference', '参考文献'],
    cross_reference: ['Cross-reference', '相互参照'],
};

const LaTeX: React.FC<ReportProps> = ({ report, onReset }) => {
    const { t, language } = useLanguage();
    const { coverage_notices: notices, issues } = report;
    const isPasj = report.detected_template === 'pasj';

    return (
        <div className="py-2">
            {/* Header with Title and Reset Button */}
            <div className="d-flex justify-content-between align-items-center mb-3">
                <h2 className="h4 text-dark font-weight-bold mb-0">
                    {t('reportTitle')}: {report.filename}
                </h2>
                {onReset && (
                    <button className="btn btn-outline-primary btn-sm" onClick={onReset}>
                        <i className="fas fa-plus mr-1"></i> {t('backToUpload')}
                    </button>
                )}
            </div>

            {/* Template Badge & Guidelines Links */}
            <div className="d-flex align-items-center flex-wrap mb-4">
                <span className="badge badge-primary mr-3 py-1 px-2 font-weight-normal">
                    {isPasj ? (language === 'ja' ? 'PASJ 和文原稿' : 'PASJ Japanese Manuscript')
                            : (language === 'ja' ? 'JACoW 英文原稿' : 'JACoW English Manuscript')}
                </span>

                {report.total_references !== undefined && (
                    <span className="badge badge-light border text-secondary mr-3 py-1 px-2 font-weight-normal">
                        <i className="fas fa-quote-right mr-1"></i>
                        {report.total_references} {language === 'ja' ? '文献を検査' : 'References Inspected'}
                    </span>
                )}

                {isPasj ? (
                    <>
                        <a href="https://www.pasj.jp/templates.html" target="_blank" rel="noreferrer" className="text-primary font-weight-bold mr-3 small">
                            <i className="fas fa-external-link-alt mr-1"></i> PASJ 論文執筆要領・テンプレート
                        </a>
                        <a href="https://www.pasj.jp/" target="_blank" rel="noreferrer" className="text-secondary font-weight-bold mr-3 small">
                            <i className="fas fa-university mr-1"></i> 日本加速器学会 (PASJ)
                        </a>
                    </>
                ) : (
                    <>
                        <a href="https://www.jacow.org/Authors/FormattingCitations" target="_blank" rel="noreferrer" className="text-primary font-weight-bold mr-3 small">
                            <i className="fas fa-external-link-alt mr-1"></i> JACoW Citation Guidelines
                        </a>
                        <a href="https://refs.jacow.org/" target="_blank" rel="noreferrer" className="text-secondary font-weight-bold mr-3 small">
                            <i className="fas fa-search mr-1"></i> JACoW Reference Search
                        </a>
                        <a href="https://www.jacow.org/Authors" target="_blank" rel="noreferrer" className="text-secondary font-weight-bold small">
                            <i className="fas fa-question-circle mr-1"></i> {t('guidelineHelp')}
                        </a>
                    </>
                )}
            </div>

            {notices.length > 0 ? (
                <section className="alert alert-warning mb-4" aria-labelledby="latex-coverage">
                    <h5 id="latex-coverage" className="alert-heading">
                        {language === 'ja' ? '未検査の項目があります' : 'Some checks could not be completed'}
                    </h5>
                    <ul className="mb-0 pl-3">
                        {notices.map((notice, idx) => (
                            <li key={idx}>
                                {notice.file ? <><code className="text-break">{notice.file}{notice.line ? ':' + notice.line : ''}</code>{' '}</> : null}
                                {language === 'ja' ? notice.message_ja || notice.message : notice.message}
                            </li>
                        ))}
                    </ul>
                </section>
            ) : null}

            {issues.length === 0 && notices.length === 0 ? (
                <div className="card shadow-sm border-0 p-4 mb-4">
                    <div className="alert alert-success d-flex align-items-center mb-0">
                        <i className="fas fa-check-circle fa-2x mr-3 text-success"></i>
                        <div>
                            <h5 className="alert-heading font-weight-bold mb-1">
                                {language === 'ja' ? '検査した項目に問題は見つかりませんでした' : 'No issues in the checked content'}
                            </h5>
                            <div className="small">
                                {isPasj
                                    ? (language === 'ja' ? 'PASJ の LaTeX ソース検査で問題は検出されませんでした。' : 'The PASJ LaTeX source checks found no issues.')
                                    : t('latexNoIssues')}
                            </div>
                        </div>
                    </div>
                </div>
            ) : null}

            {issues.length > 0 ? (
                <div className="card shadow-sm border-0 mb-4">
                    <div className="card-header bg-light d-flex justify-content-between align-items-center py-3">
                        <div className="d-flex align-items-center">
                            <i className="fas fa-exclamation-circle text-danger mr-2 fa-lg"></i>
                            <span className="font-weight-bold text-dark h6 mb-0">
                                {language === 'ja' ? '検出された書式・引用違反項目 (Validation Issues)' : t('latexIssuesDetected')}
                            </span>
                        </div>
                        <span className="badge badge-danger text-white px-3 py-1 font-weight-bold">
                            {issues.length} {language === 'ja' ? '件の修正要求' : t('latexIssueCount')}
                        </span>
                    </div>

                    <div className="card-body p-0">
                        <div className="table-responsive">
                            <table className="table table-bordered table-hover mb-0">
                                <thead className="thead-light">
                                    <tr>
                                        <th style={{ width: '50px' }} className="text-center">#</th>
                                        <th style={{ width: '80px' }} className="text-center">{language === 'ja' ? '状態' : 'Status'}</th>
                                        <th style={{ width: '220px' }}>{language === 'ja' ? '検査項目 / 箇所' : 'Category / Target'}</th>
                                        <th>{language === 'ja' ? '違反内容と改善提案' : 'Violation Details & Suggestion'}</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {issues.map((issue, idx) => {
                                        const category = issue.category && categories[issue.category];
                                        const label = category ? category[language === 'ja' ? 1 : 0] : issue.name;
                                        const description = language === 'ja' ? issue.message_ja || issue.message : issue.message;
                                        return (
                                            <tr key={idx}>
                                                <td className="text-center font-weight-bold text-muted align-middle">
                                                    {idx + 1}
                                                </td>
                                                <td className="text-center align-middle">
                                                    <span className="badge badge-danger px-2 py-1">Error</span>
                                                </td>
                                                <td className="align-middle">
                                                    <span className="badge badge-secondary px-2 py-1 font-weight-normal" style={{ fontSize: '0.85rem' }}>
                                                        {label}
                                                    </span>
                                                    {(issue.category === 'reference' || issue.category === 'cross_reference') && (
                                                        <code className="d-block mt-1 text-break">{issue.name}</code>
                                                    )}
                                                    {issue.file ? (
                                                        <code className="d-block mt-1 text-break">
                                                            {issue.file}{issue.line ? ':' + issue.line : ''}
                                                        </code>
                                                    ) : null}
                                                </td>
                                                <td className="small text-dark" style={{ lineHeight: '1.6', whiteSpace: 'pre-wrap' }}>
                                                    {description}
                                                </td>
                                            </tr>
                                        );
                                    })}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            ) : null}
        </div>
    );
};

export type { LaTeXReport };
export default LaTeX;
