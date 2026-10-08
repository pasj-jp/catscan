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
};

type ReportProps = {
    report: LaTeXReport,
    onReset?: () => void,
};

const LaTeX: React.FC<ReportProps> = (props) => {
    const { t } = useLanguage();
    const { report, onReset } = props;

    // Parse issue items from unabbreviated text
    const rawIssues = (report.unabbreviated || report.content || "")
        .split("\n\n")
        .map(s => s.trim())
        .filter(s => s.length > 0 && s.startsWith("Issue found in reference"));

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

            {/* Reference Guidelines Links */}
            <div className="mb-4">
                <a href="https://www.jacow.org/Authors/FormattingCitations" target="_blank" rel="noreferrer" className="text-primary font-weight-bold mr-3 small">
                    <i className="fas fa-external-link-alt mr-1"></i> JACoW Citation Guidelines
                </a>
                <a href="https://refs.jacow.org/" target="_blank" rel="noreferrer" className="text-secondary font-weight-bold mr-3 small">
                    <i className="fas fa-search mr-1"></i> JACoW Reference Search
                </a>
                <a href="https://www.jacow.org/Authors/CSEHelp" target="_blank" rel="noreferrer" className="text-secondary font-weight-bold small">
                    <i className="fas fa-question-circle mr-1"></i> {t('guidelineHelp')}
                </a>
            </div>

            {/* Results Section */}
            {report.issuesFound === 0 ? (
                <div className="card shadow-sm border-0 p-4 mb-4">
                    <div className="alert alert-success d-flex align-items-center mb-0">
                        <i className="fas fa-check-circle fa-2x mr-3 text-success"></i>
                        <div>
                            <h5 className="alert-heading font-weight-bold mb-1">OK</h5>
                            <div className="small">{t('latexNoIssues')}</div>
                        </div>
                    </div>
                </div>
            ) : (
                <div className="card shadow-sm border-0 mb-4">
                    <div className="card-header bg-light d-flex justify-content-between align-items-center py-3">
                        <span className="font-weight-bold text-dark">
                            {t('latexIssuesDetected')}
                        </span>
                        <span className="badge badge-warning text-dark px-2 py-1">
                            {report.issuesFound} {t('latexIssueCount')}
                        </span>
                    </div>
                    <div className="card-body">
                        {report.isAbbreviated ? (
                            <div className="mb-3">
                                <ReactMarkdown>{report.content}</ReactMarkdown>
                            </div>
                        ) : null}

                        {rawIssues.length > 0 ? (
                            <div className="list-group list-group-flush">
                                {rawIssues.map((issueText, idx) => {
                                    // Extract reference name and description
                                    const match = issueText.match(/^Issue found in reference\s+([^:]+):\s*(.*)$/s);
                                    const refName = match ? match[1].trim() : `Issue #${idx + 1}`;
                                    const refDesc = match ? match[2].trim() : issueText;

                                    return (
                                        <div key={idx} className="list-group-item px-0 py-3">
                                            <div className="d-flex align-items-start">
                                                <span className="badge badge-danger mr-2 mt-1">Error</span>
                                                <div>
                                                    <strong className="text-dark">Reference [{refName}]:</strong>
                                                    <div className="text-secondary small mt-1">{refDesc}</div>
                                                </div>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        ) : (
                            <div className="text-secondary small">
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