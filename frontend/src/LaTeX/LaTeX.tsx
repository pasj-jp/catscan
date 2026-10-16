import React from "react";
import './Report.css';
import ReactMarkdown from 'react-markdown';
import { useLanguage } from "../i18n";

type LaTeXReport = {
    filename: string,
    content: string,
    isAbbreviated: boolean,
    unabbreviated: string,
    issuesFound: number,
    detected_template?: string,
    template_name?: string,
    total_references?: number,
};

type ReportProps = {
    report: LaTeXReport,
    onReset?: () => void,
};

interface ParsedIssue {
    target: string;
    description: string;
}

const getCategoryBadge = (target: string, language: string) => {
    const t = target.toLowerCase();
    if (t.includes('documentclass')) {
        return language === 'ja' ? '文書クラス (documentclass)' : 'Document Class';
    }
    if (t.includes('jtitle') || t === 'title') {
        return language === 'ja' ? '題名・タイトル (title)' : 'Title';
    }
    if (t.includes('author') || t.includes('jauthor')) {
        return language === 'ja' ? '著者名表記 (authors)' : 'Authors';
    }
    if (t.includes('abstract')) {
        return language === 'ja' ? '英文要旨 (abstract)' : 'Abstract';
    }
    if (t.includes('punctuation')) {
        return language === 'ja' ? '本文句読点 (punctuation)' : 'Punctuation';
    }
    if (t.includes('figure') || t.includes('fig')) {
        return language === 'ja' ? '図キャプション (figure)' : 'Figure Caption';
    }
    if (t.includes('table') || t.includes('tbl')) {
        return language === 'ja' ? '表タイトル (table)' : 'Table Title';
    }
    if (t.startsWith('reference') || t.includes('bad') || t.includes('ref') || t.includes('pasj_bad')) {
        return `${language === 'ja' ? '参考文献' : 'Reference'} [${target.replace(/^reference\s+/i, '')}]`;
    }
    return target;
};

const LaTeX: React.FC<ReportProps> = (props) => {
    const { t, language } = useLanguage();
    const { report, onReset } = props;

    // Parse issue items from unabbreviated or content text
    const textToParse = report.unabbreviated || report.content || "";
    const rawBlocks = textToParse
        .split("\n\n")
        .map(s => s.trim())
        .filter(s => s.length > 0 && s.startsWith("Issue found in "));

    const parsedIssues: ParsedIssue[] = rawBlocks.map((block, idx) => {
        const match = block.match(/^Issue found in\s+([^:]+):\s*([\s\S]*)$/);
        if (match) {
            return {
                target: match[1].trim(),
                description: match[2].trim(),
            };
        }
        return {
            target: `Issue #${idx + 1}`,
            description: block,
        };
    });

    const isPasj = report.detected_template === 'pasj' || 
                   (report.template_name && report.template_name.includes('PASJ')) ||
                   textToParse.includes('PASJ') ||
                   rawBlocks.some(b => b.includes('PASJ'));

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
                        <a href="https://www.jacow.org/Authors/CSEHelp" target="_blank" rel="noreferrer" className="text-secondary font-weight-bold small">
                            <i className="fas fa-question-circle mr-1"></i> {t('guidelineHelp')}
                        </a>
                    </>
                )}
            </div>

            {/* Results Section */}
            {report.issuesFound === 0 ? (
                <div className="card shadow-sm border-0 p-4 mb-4">
                    <div className="alert alert-success d-flex align-items-center mb-0">
                        <i className="fas fa-check-circle fa-2x mr-3 text-success"></i>
                        <div>
                            <h5 className="alert-heading font-weight-bold mb-1">
                                {language === 'ja' ? '合格 (All Passed)' : 'OK - All Passed'}
                            </h5>
                            <div className="small">
                                {isPasj 
                                    ? (language === 'ja' ? 'すべての書式、句読点、英文要旨および参考文献がPASJ執筆基準を満たしています。' : 'All formatting, punctuation, English abstract, and citations comply with PASJ rules.')
                                    : t('latexNoIssues')}
                            </div>
                        </div>
                    </div>
                </div>
            ) : (
                <div className="card shadow-sm border-0 mb-4">
                    <div className="card-header bg-light d-flex justify-content-between align-items-center py-3">
                        <div className="d-flex align-items-center">
                            <i className="fas fa-exclamation-circle text-danger mr-2 fa-lg"></i>
                            <span className="font-weight-bold text-dark h6 mb-0">
                                {language === 'ja' ? '検出された書式・引用違反項目 (Validation Issues)' : t('latexIssuesDetected')}
                            </span>
                        </div>
                        <span className="badge badge-danger text-white px-3 py-1 font-weight-bold">
                            {report.issuesFound} {language === 'ja' ? '件の修正要求' : t('latexIssueCount')}
                        </span>
                    </div>

                    <div className="card-body p-0">
                        {report.isAbbreviated ? (
                            <div className="p-3 border-bottom bg-light small">
                                <ReactMarkdown>{report.content}</ReactMarkdown>
                            </div>
                        ) : null}

                        {parsedIssues.length > 0 ? (
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
                                        {parsedIssues.map((issue, idx) => {
                                            const categoryLabel = getCategoryBadge(issue.target, language);
                                            let displayDesc = issue.description;
                                            if (displayDesc.includes(' / ')) {
                                                const parts = displayDesc.split(' / ');
                                                if (parts.length === 2 && /[^\x00-\x7F]/.test(parts[0])) {
                                                    displayDesc = language === 'ja'
                                                        ? `${parts[0]}\n(${parts[1]})`
                                                        : `${parts[1]}\n(${parts[0]})`;
                                                }
                                            }
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
                                                            {categoryLabel}
                                                        </span>
                                                    </td>
                                                    <td className="small text-dark" style={{ lineHeight: '1.6', whiteSpace: 'pre-wrap' }}>
                                                        {displayDesc}
                                                    </td>
                                                </tr>
                                            );
                                        })}
                                    </tbody>
                                </table>
                            </div>
                        ) : (
                            <div className="p-3 text-secondary small">
                                {report.content.split('\n').map((line, idx) => (
                                    <div key={idx}>{line}</div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
};

export type { LaTeXReport };
export default LaTeX;