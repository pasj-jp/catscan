import React from "react";
import { useLanguage } from "../i18n";

const Resources: React.FC = () => {
    const { t } = useLanguage();

    return (
        <div className="py-4">
            <h2 className="h4 font-weight-bold text-dark mb-4">
                {t('resourcesTitle')}
            </h2>

            <div className="row">
                {/* PASJ Section */}
                <div className="col-lg-7 mb-4">
                    <div className="card shadow-sm border-0 mb-4">
                        <div className="card-header bg-light font-weight-bold text-dark py-3">
                            {t('pasjSection')}
                        </div>
                        <div className="card-body">
                            <p className="card-text text-muted small mb-3">
                                {t('pasjDesc')}
                            </p>

                            <div className="list-group list-group-flush mb-4 small">
                                <a href="https://www.pasj.jp/templates/nenkai/Proc_Template2026_Word.dotx" 
                                   target="_blank" rel="noreferrer" 
                                   className="list-group-item list-group-item-action d-flex justify-content-between align-items-center px-0 py-2 border-top-0">
                                    <span>{t('wordTemplate')}</span>
                                    <span className="badge badge-light border">.dotx</span>
                                </a>
                                <a href="https://www.pasj.jp/templates/nenkai/Proc_Template2026_Word.pdf" 
                                   target="_blank" rel="noreferrer" 
                                   className="list-group-item list-group-item-action d-flex justify-content-between align-items-center px-0 py-2">
                                    <span>{t('wordSample')}</span>
                                    <span className="badge badge-light border">PDF</span>
                                </a>
                                <a href="https://www.pasj.jp/templates/nenkai/Proc_Template2026_tex.zip" 
                                   target="_blank" rel="noreferrer" 
                                   className="list-group-item list-group-item-action d-flex justify-content-between align-items-center px-0 py-2">
                                    <span>{t('texTemplate')}</span>
                                    <span className="badge badge-light border">.zip</span>
                                </a>
                                <a href="https://pasj.jp/templates.html" 
                                   target="_blank" rel="noreferrer" 
                                   className="list-group-item list-group-item-action d-flex justify-content-between align-items-center px-0 py-2">
                                    <span>{t('pasjOfficialPage')}</span>
                                    <span className="badge badge-light border">Web</span>
                                </a>
                            </div>

                            {/* Checklist Section inside Resources */}
                            <div className="card bg-light border-0 p-3">
                                <h6 className="font-weight-bold text-dark mb-2">
                                    {t('pasjChecklistTitle')}
                                </h6>
                                <ol className="small text-secondary pl-3 mb-0" style={{ lineHeight: '1.7' }}>
                                    <li className="mb-2">{t('checkA4')}</li>
                                    <li className="mb-2">{t('checkTemplate')}</li>
                                    <li className="mb-2">{t('checkBilingual')}</li>
                                    <li className="mb-2">{t('checkPunctuation')}</li>
                                    <li className="mb-2">{t('checkCaptions')}</li>
                                    <li className="mb-2">{t('checkSpacing')}</li>
                                    <li>{t('checkFonts')}</li>
                                </ol>
                            </div>
                        </div>
                    </div>
                </div>

                {/* JACoW English Section */}
                <div className="col-lg-5 mb-4">
                    <div className="card shadow-sm border-0 mb-4">
                        <div className="card-header bg-light font-weight-bold text-dark py-3">
                            {t('jacowSection')}
                        </div>
                        <div className="card-body">
                            <p className="card-text text-muted small mb-3">
                                {t('jacowDesc')}
                            </p>

                            <div className="list-group list-group-flush mb-3 small">
                                <a href="https://www.jacow.org/Authors/MSWord" target="_blank" rel="noreferrer" 
                                   className="list-group-item list-group-item-action d-flex justify-content-between align-items-center px-0 py-2 border-top-0">
                                    <span>{t('jacowWord')}</span>
                                    <span className="badge badge-light border">Guide</span>
                                </a>
                                <a href="https://www.jacow.org/Authors/LaTeX" target="_blank" rel="noreferrer" 
                                   className="list-group-item list-group-item-action d-flex justify-content-between align-items-center px-0 py-2">
                                    <span>{t('jacowLatex')}</span>
                                    <span className="badge badge-light border">Guide</span>
                                </a>
                                <a href="https://www.jacow.org/Authors/FormattingCitations" target="_blank" rel="noreferrer" 
                                   className="list-group-item list-group-item-action d-flex justify-content-between align-items-center px-0 py-2">
                                    <span>{t('jacowCitations')}</span>
                                    <span className="badge badge-light border">Guide</span>
                                </a>
                                <a href="https://www.jacow.org/Authors/CSEHelp" target="_blank" rel="noreferrer" 
                                   className="list-group-item list-group-item-action d-flex justify-content-between align-items-center px-0 py-2">
                                    <span>{t('jacowHelp')}</span>
                                    <span className="badge badge-light border">Help</span>
                                </a>
                            </div>

                            <div className="alert alert-secondary py-2 small mb-0">
                                {t('pasjEnglishNote')}
                            </div>
                        </div>
                    </div>

                    <div className="card bg-light border-0 p-3 text-muted small">
                        <p className="mb-0">
                            {t('aboutNote')}
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Resources;