import React from 'react';
import Section, {SectionProps} from "./Section";
import './Report.css';
import { useLanguage } from "../i18n";

type WordReport = {
    type: string,
    filename?: string,
    detected_template?: string,
    template_name?: string,
    summary: { [key: string]: SectionProps } | SectionProps[]
    scores: {
        [key: string]: [number, number, number]
    }
};

type ReportProps = {
    report: WordReport,
    onReset?: () => void,
}

const getScores = (scores: [number, number, number]) => {
    const successCount = scores[0]
    const warningCount = scores[1]
    const errorCount = scores[2]
    const total = successCount + warningCount + errorCount
    const successPercent = total > 0 ? Math.round((successCount / total) * 100) : 0;
    const warningPercent = total > 0 ? Math.round((warningCount / total) * 100) : 0;
    const errorPercent = total > 0 ? Math.round((errorCount / total) * 100) : 0;
    return {
        'total': total, 'count': {
            'success': successCount,
            'warning': warningCount,
            'error': errorCount
        }, 'percent': {
            'success': successPercent,
            'warning': warningPercent,
            'error': errorPercent
        }
    }
}

const Word: React.FC<ReportProps> = (props) => {
    const { t, language } = useLanguage();
    const report = props.report;
    const [showAllScores, setShowAllScores] = React.useState(false);

    const totals = getScores(report.scores.total)
    return (
        <div>
            <div className="d-flex justify-content-between align-items-center mb-2">
                {report.filename &&
                    <h2 className="h4 text-dark font-weight-bold mb-0">{t('reportTitle')}: {report.filename}</h2>
                }
                {props.onReset && (
                    <button className="btn btn-outline-primary btn-sm" onClick={props.onReset}>
                        <i className="fas fa-plus mr-1"></i> {t('backToUpload')}
                    </button>
                )}
            </div>

            <div className="d-flex align-items-center mb-3">
                {report.template_name && (
                    <span className="badge badge-primary mr-3 py-1 px-2 font-weight-normal">
                        {report.detected_template === 'pasj' ? t('templatePasjName')
                            : report.detected_template === 'jacow' ? t('templateJacowName')
                            : report.template_name}
                    </span>
                )}
                <a href="https://pasj.jp/templates.html" title="PASJ Templates" rel="noreferrer" target="_blank" className="text-secondary font-weight-bold mr-3 small">
                    <i className="fas fa-external-link-alt mr-1"></i> {t('pasjGuidelines')}
                </a>
                <a href="https://www.jacow.org/Authors/CSEHelp" title="Author Help" rel="noreferrer" target="_blank" className="text-secondary font-weight-bold small">
                    <i className="fas fa-question-circle mr-1"></i> {t('guidelineHelp')}
                </a>
            </div>

            <div className="score-type mb-2">
                <h5 className="font-weight-bold text-dark">{t('scoreSummary')}</h5>
            </div>

            {showAllScores &&
                <div>
                    {Object.entries(report.scores)
                        .map((section) => {
                            if (section[0] === 'total') {
                                return null;
                            }
                            const scores = getScores(section[1])
                            if (scores.total === 0) {
                                return null;
                            }

                            return (
                                <div key={section[0]} className="scores mb-2">
                                    <div className="small font-weight-bold text-secondary">{section[0]}</div>
                                    <div className="progress">
                                        <div className="progress-bar bg-success" role="progressbar"
                                             style={{width: scores.percent.success + '%'}}>
                                            {scores.count.success} {t('scoreOk')}
                                        </div>
                                        <div className="progress-bar bg-warning" role="progressbar"
                                             style={{width: scores.percent.warning + '%'}}>
                                            {scores.count.warning} {t('scoreWarnings')}
                                        </div>
                                        <div className="progress-bar bg-danger" role="progressbar"
                                             style={{width: scores.percent.error + '%'}}>
                                            {scores.count.error} {t('scoreErrors')}
                                        </div>
                                    </div>
                                </div>
                            );
                        })}
                </div>}

            <div className="scores mb-3">
                <div className="small font-weight-bold text-dark">{t('overall')}</div>
                <div className="progress" style={{ height: '22px' }}>
                    <div className="progress-bar bg-success" role="progressbar"
                         style={{width: totals.percent.success + '%'}}>
                        {totals.count.success} {t('scoreOk')}
                    </div>
                    <div className="progress-bar bg-warning" role="progressbar"
                         style={{width: totals.percent.warning + '%'}}>
                        {totals.count.warning} {t('scoreWarnings')}
                    </div>
                    <div className="progress-bar bg-danger" role="progressbar"
                         style={{width: totals.percent.error + '%'}}>
                        {totals.count.error} {t('scoreErrors')}
                    </div>
                </div>
            </div>

            <div className="my-2 mb-4">
                <button onClick={() => setShowAllScores(!showAllScores)} 
                        className="btn btn-sm btn-outline-secondary" type="button">
                    {!showAllScores && <><i className="fas fa-chevron-down mr-1"></i> {language === 'ja' ? '詳細スコアを表示' : 'Show all scores'}</>}
                    {showAllScores && <><i className="fas fa-chevron-up mr-1"></i> {language === 'ja' ? '詳細スコアを隠す' : 'Hide scores'}</>}
                </button>
            </div>

            {/* Detailed Section Reports grouped by Status: Errors -> Warnings -> OK */}
            {report.summary && (
                Array.isArray(report.summary) ? (
                    <div>
                        {report.summary.map((section, index) => (
                            <Section key={index} {...section} />
                        ))}
                    </div>
                ) : (
                    <div className="ok-type mt-4">
                        {/* 1. Errors */}
                        {Object.values(report.summary).some((s: any) => s.ok === false) && (
                            <div className="mb-4">
                                <h4 className="text-danger font-weight-bold mb-3 d-flex align-items-center">
                                    <i className="fas fa-times-circle mr-2"></i>
                                    {language === 'ja' ? '要修正項目 (Errors)' : 'Errors'}
                                </h4>
                                <div>
                                    {Object.entries(report.summary).map(([name, section]) => {
                                        if (section.ok === false) {
                                            return <Section key={name} name={name} {...section} />;
                                        }
                                        return null;
                                    })}
                                </div>
                            </div>
                        )}

                        {/* 2. Warnings */}
                        {Object.values(report.summary).some((s: any) => s.ok === 2) && (
                            <div className="mb-4">
                                <h4 className="text-warning font-weight-bold mb-3 d-flex align-items-center">
                                    <i className="fas fa-exclamation-triangle mr-2"></i>
                                    {language === 'ja' ? '警告項目 (Warnings)' : 'Warnings'}
                                </h4>
                                <div>
                                    {Object.entries(report.summary).map(([name, section]) => {
                                        if (section.ok === 2) {
                                            return <Section key={name} name={name} {...section} />;
                                        }
                                        return null;
                                    })}
                                </div>
                            </div>
                        )}

                        {/* 3. Conforms to Standard */}
                        {Object.values(report.summary).some((s: any) => s.ok === true) && (
                            <div className="mb-4">
                                <h4 className="text-success font-weight-bold mb-3 d-flex align-items-center">
                                    <i className="fas fa-check-circle mr-2"></i>
                                    {language === 'ja' ? '適合項目 (Conforms to Standard)' : 'Conforms to Standard'}
                                </h4>
                                <div>
                                    {Object.entries(report.summary).map(([name, section]) => {
                                        if (section.ok === true) {
                                            return <Section key={name} name={name} {...section} />;
                                        }
                                        return null;
                                    })}
                                </div>
                            </div>
                        )}
                    </div>
                )
            )}
        </div>
    );
}

export type {WordReport};
export default Word;
