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

const CATEGORY_NAMES_JA: { [key: string]: string } = {
    Title: '題名 (Title)',
    Authors: '著者名・所属 (Authors)',
    Abstract: 'アブストラクト (Abstract)',
    Headings: '見出し (Headings)',
    Paragraphs: '本文・句読点 (Paragraphs)',
    Figures: '図キャプション (Figures)',
    Tables: '表キャプション (Tables)',
    References: '参考文献 (References)',
    Margins: '余白・ページ設定 (Margins)',
    Styles: 'PASJスタイル・ページ数 (Styles)',
    Document: '文書全般 (Document)',
};

const Word: React.FC<ReportProps> = (props) => {
    const { t, language } = useLanguage();
    const report = props.report;
    const [showAllScores, setShowAllScores] = React.useState(true);

    const totals = getScores(report.scores.total);
    const isPasj = report.detected_template === 'pasj' || (report.template_name && report.template_name.includes('PASJ'));

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

            <div className="d-flex align-items-center flex-wrap mb-3">
                {report.template_name && (
                    <span className="badge badge-primary mr-3 py-1 px-2 font-weight-normal">
                        {report.detected_template === 'pasj' ? t('templatePasjName')
                            : report.detected_template === 'jacow' ? t('templateJacowName')
                            : report.template_name}
                    </span>
                )}
                {totals.count.error === 0 && totals.count.warning === 0 && (
                    <span className="badge badge-success mr-3 py-1 px-2">
                        <i className="fas fa-check-circle mr-1"></i>
                        {language === 'ja' ? '合格 (PASSED)' : 'PASSED'}
                    </span>
                )}
                {totals.count.error === 0 && totals.count.warning > 0 && (
                    <span className="badge badge-warning text-dark mr-3 py-1 px-2">
                        <i className="fas fa-exclamation-triangle mr-1"></i>
                        {language === 'ja' ? '条件付合格・要確認 (WARNINGS)' : 'PASSED WITH WARNINGS'}
                    </span>
                )}
                {totals.count.error > 0 && (
                    <span className="badge badge-danger mr-3 py-1 px-2">
                        <i className="fas fa-times-circle mr-1"></i>
                        {language === 'ja' ? `要修正 (${totals.count.error} 件のエラー)` : `REVISION REQUIRED (${totals.count.error} Errors)`}
                    </span>
                )}
                {isPasj ? (
                    <a href="https://www.pasj.jp/templates.html" title="PASJ Templates" rel="noreferrer" target="_blank" className="text-primary font-weight-bold mr-3 small">
                        <i className="fas fa-external-link-alt mr-1"></i> {t('pasjGuidelines')}
                    </a>
                ) : (
                    <>
                        <a href="https://www.jacow.org/Authors/MSWord" title="JACoW MSWord Guidelines" rel="noreferrer" target="_blank" className="text-primary font-weight-bold mr-3 small">
                            <i className="fas fa-external-link-alt mr-1"></i> JACoW Word Guidelines
                        </a>
                        <a href="https://www.jacow.org/Authors/CSEHelp" title="Author Help" rel="noreferrer" target="_blank" className="text-secondary font-weight-bold small">
                            <i className="fas fa-question-circle mr-1"></i> {t('guidelineHelp')}
                        </a>
                    </>
                )}
            </div>

            <div className="score-type mb-2 d-flex justify-content-between align-items-center">
                <h5 className="font-weight-bold text-dark mb-0">{t('scoreSummary')}</h5>
                <button onClick={() => setShowAllScores(!showAllScores)} 
                        className="btn btn-sm btn-outline-secondary" type="button">
                    {!showAllScores && <><i className="fas fa-chevron-down mr-1"></i> {language === 'ja' ? 'カテゴリ別スコアを表示' : 'Show category scores'}</>}
                    {showAllScores && <><i className="fas fa-chevron-up mr-1"></i> {language === 'ja' ? 'カテゴリ別スコアを隠す' : 'Hide category scores'}</>}
                </button>
            </div>

            <div className="scores mb-3">
                <div className="d-flex justify-content-between small font-weight-bold text-dark mb-1">
                    <span>{t('overall')}</span>
                    <span>
                        <span className="text-success mr-2">✓ {totals.count.success} {t('scoreOk')}</span>
                        <span className="text-warning mr-2">⚠ {totals.count.warning} {t('scoreWarnings')}</span>
                        <span className="text-danger">✗ {totals.count.error} {t('scoreErrors')}</span>
                    </span>
                </div>
                <div className="progress" style={{ height: '22px' }}>
                    <div className="progress-bar bg-success" role="progressbar"
                         style={{width: totals.percent.success + '%'}}>
                        {totals.count.success > 0 ? `${totals.count.success} ${t('scoreOk')}` : ''}
                    </div>
                    <div className="progress-bar bg-warning text-dark" role="progressbar"
                         style={{width: totals.percent.warning + '%'}}>
                        {totals.count.warning > 0 ? `${totals.count.warning} ${t('scoreWarnings')}` : ''}
                    </div>
                    <div className="progress-bar bg-danger" role="progressbar"
                         style={{width: totals.percent.error + '%'}}>
                        {totals.count.error > 0 ? `${totals.count.error} ${t('scoreErrors')}` : ''}
                    </div>
                </div>
            </div>

            {showAllScores &&
                <div className="card card-body bg-light border-0 py-2 px-3 mb-4">
                    {Object.entries(report.scores)
                        .map((section) => {
                            if (section[0] === 'total') {
                                return null;
                            }
                            const scores = getScores(section[1])
                            if (scores.total === 0) {
                                return null;
                            }
                            const displayCat = language === 'ja' ? (CATEGORY_NAMES_JA[section[0]] || section[0]) : section[0];

                            return (
                                <div key={section[0]} className="scores mb-2">
                                    <div className="d-flex justify-content-between small font-weight-bold text-secondary mb-1">
                                        <span>{displayCat}</span>
                                        <span>
                                            <span className="text-success mr-2">{scores.count.success} OK</span>
                                            {scores.count.warning > 0 && <span className="text-warning mr-2">{scores.count.warning} Warn</span>}
                                            {scores.count.error > 0 && <span className="text-danger">{scores.count.error} Error</span>}
                                        </span>
                                    </div>
                                    <div className="progress" style={{ height: '14px' }}>
                                        <div className="progress-bar bg-success" role="progressbar"
                                             style={{width: scores.percent.success + '%'}}>
                                        </div>
                                        <div className="progress-bar bg-warning" role="progressbar"
                                             style={{width: scores.percent.warning + '%'}}>
                                        </div>
                                        <div className="progress-bar bg-danger" role="progressbar"
                                             style={{width: scores.percent.error + '%'}}>
                                        </div>
                                    </div>
                                </div>
                            );
                        })}
                </div>}

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
