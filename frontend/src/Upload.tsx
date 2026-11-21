import React from 'react';
import { isAxiosError } from 'axios';
import { Accept, useDropzone } from 'react-dropzone';
import api from './api';
import './Upload.css';
import { Report } from "./App";
import { useSearchParams } from "react-router-dom";
import { useLanguage } from "./i18n";

type UploadState = "idle" | "processing" | "error";
type ManualTemplate = 'pasj' | 'jacow';
type TemplateChoice = 'auto' | ManualTemplate;

type TemplateMismatch = {
    file: File;
    selected: ManualTemplate;
    detected: ManualTemplate;
};

type ScanError = {
    code?: string;
    error?: string;
    detected_template?: ManualTemplate;
};

const allowedExtensions: Accept = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
    "application/x-tex": [".tex"],
    "application/zip": [".zip"],
    "application/x-zip-compressed": [".zip"],
    "application/gzip": [".tar.gz", ".tgz"],
    "application/x-gzip": [".tar.gz", ".tgz"],
};

type UploadProps = {
    setReport: (report: Report) => void
}

const TemplateMismatchDialog: React.FC<{
    mismatch: TemplateMismatch;
    onChoose: (template: ManualTemplate) => void;
    onCancel: () => void;
}> = ({ mismatch, onChoose, onCancel }) => {
    const { t } = useLanguage();
    const dialogRef = React.useRef<HTMLDialogElement>(null);
    React.useEffect(() => {
        const dialog = dialogRef.current;
        dialog?.showModal();
        return () => dialog?.close();
    }, []);

    const selected = t(mismatch.selected === 'pasj' ? 'templatePasjName' : 'templateJacowName');
    const detected = t(mismatch.detected === 'pasj' ? 'templatePasjName' : 'templateJacowName');
    return (
        <dialog
            className="template-mismatch"
            ref={dialogRef}
            aria-labelledby="template-mismatch-title"
            aria-describedby="template-mismatch-description"
            onCancel={onCancel}
        >
            <div className="modal-header">
                <h2 className="modal-title h5" id="template-mismatch-title">{t('templateMismatchTitle')}</h2>
                <button type="button" className="close" aria-label={t('templateMismatchCancel')} onClick={onCancel}>
                    <span aria-hidden="true">×</span>
                </button>
            </div>
            <div className="modal-body" id="template-mismatch-description">
                <p className="mb-2">{t('templateMismatchSelected')} <strong>{selected}</strong></p>
                <p className="mb-0">{t('templateMismatchDetected')} <strong>{detected}</strong></p>
            </div>
            <div className="modal-footer">
                <button type="button" className="btn btn-outline-secondary" onClick={() => onChoose(mismatch.selected)}>
                    {t('templateMismatchKeep')}
                </button>
                <button type="button" className="btn btn-primary" autoFocus onClick={() => onChoose(mismatch.detected)}>
                    {t('templateMismatchSwitch')}
                </button>
            </div>
        </dialog>
    );
};

const Upload: React.FC<UploadProps> = (props) => {
    const { t } = useLanguage();
    const [searchParams, setSearchParams] = useSearchParams();
    const [selectedTemplate, setSelectedTemplate] = React.useState<TemplateChoice>('pasj');
    const [mismatch, setMismatch] = React.useState<TemplateMismatch | null>(null);
    const [progress, setProgress] = React.useState(0);
    const [upload, setUpload] = React.useState<UploadState>('idle');
    const [error, setError] = React.useState<string>('');

    const opts = {
        accept: allowedExtensions,
        multiple: false,
    };

    const resultsId = searchParams.get("results");
    React.useEffect(() => {
        if (!resultsId) return;
        const controller = new AbortController();
        setUpload("processing");
        api.get<Report>(`/api/reports/${encodeURIComponent(resultsId)}`, { signal: controller.signal })
            .then(({ data }) => props.setReport(data))
            .catch(() => {
                if (controller.signal.aborted) return;
                setUpload("error");
                setError(t('reportLoadError'));
            });
        return () => controller.abort();
    }, [resultsId, props.setReport, t]);

    const restart = () => {
        setProgress(0);
        setUpload('idle');
        setError('');
    };

    const { getRootProps, getInputProps, acceptedFiles } = useDropzone(opts);
    const scan = async (file: File, template: TemplateChoice, verifyTemplate: boolean) => {
        setProgress(0);
        setUpload("processing");
        const formData = new FormData();
        formData.append("file", file);
        formData.append("template", template);
        formData.append("verify_template", String(verifyTemplate));
        try {
            const response = await api.post<Report>("/api/scan/file", formData, {
                onUploadProgress: (event) => {
                    if (event.progress !== undefined) {
                        setProgress(Math.round(event.progress * 100));
                    }
                },
            });
            if (response.data.report_id) {
                setSearchParams({ results: response.data.report_id });
            }
            props.setReport(response.data);
        } catch (err) {
            const response = isAxiosError<ScanError>(err) ? err.response : undefined;
            const errorData = response?.data;
            const detected = errorData?.detected_template;
            if (verifyTemplate && template !== 'auto' && errorData?.code === 'template_mismatch'
                && (detected === 'pasj' || detected === 'jacow')) {
                setMismatch({ file, selected: template, detected });
                setUpload("idle");
                return;
            }
            setUpload("error");
            if (isAxiosError(err) && !errorData?.error && (!response || response.status >= 500)) {
                setError(t('scanServiceUnavailable'));
            } else {
                setError(errorData?.error || (err instanceof Error ? err.message : t('errorTitle')));
            }
        }
    };

    return (
        <div className="row justify-content-center my-3">
            <div className="col-lg-8 col-xl-7">
                {upload === 'idle' && (
                    <form onSubmit={(e) => {
                        e.preventDefault();
                        if (acceptedFiles[0]) {
                            void scan(acceptedFiles[0], selectedTemplate, selectedTemplate !== 'auto');
                        }
                    }} className="card shadow-sm border-0 p-4 p-md-5">

                        <div className="text-center mb-4">
                            <h2 className="h4 font-weight-bold text-dark mb-2">
                                {t('uploadTitle')}
                            </h2>
                            <p className="text-muted small mb-0">
                                {t('uploadSubtitle')}
                            </p>
                        </div>

                        {/* Format Selection (Auto / PASJ Japanese / JACoW English) */}
                        <div className="form-group mb-4">
                            <label className="font-weight-bold text-secondary mb-2 d-block">
                                {t('templateLabel')}
                            </label>
                            <div className="btn-group btn-group-toggle w-100 shadow-sm" role="group">
                                <button
                                    type="button"
                                    aria-pressed={selectedTemplate === 'auto'}
                                    className={`btn py-2 ${selectedTemplate === 'auto' ? 'btn-primary font-weight-bold' : 'btn-outline-secondary'}`}
                                    onClick={() => setSelectedTemplate('auto')}
                                    style={{ width: '30%' }}
                                >
                                    <i className="fas fa-magic mr-2"></i> {t('templateAuto')}
                                </button>
                                <button
                                    type="button"
                                    aria-pressed={selectedTemplate === 'pasj'}
                                    className={`btn py-2 ${selectedTemplate === 'pasj' ? 'btn-primary font-weight-bold' : 'btn-outline-secondary'}`}
                                    onClick={() => setSelectedTemplate('pasj')}
                                    style={{ width: '35%' }}
                                >
                                    <i className="fas fa-file-alt mr-2"></i> {t('templatePasj')}
                                </button>
                                <button
                                    type="button"
                                    aria-pressed={selectedTemplate === 'jacow'}
                                    className={`btn py-2 ${selectedTemplate === 'jacow' ? 'btn-primary font-weight-bold' : 'btn-outline-secondary'}`}
                                    onClick={() => setSelectedTemplate('jacow')}
                                    style={{ width: '35%' }}
                                >
                                    <i className="fas fa-globe mr-2"></i> {t('templateJacow')}
                                </button>
                            </div>
                            <small className="form-text text-muted mt-2">
                                <i className="fas fa-info-circle mr-1"></i>
                                {selectedTemplate === 'auto'
                                    ? t('templateAutoDesc')
                                    : selectedTemplate === 'pasj'
                                        ? t('templatePasjDesc')
                                        : t('templateJacowDesc')}
                            </small>
                        </div>

                        {/* Dropzone */}
                        <div className="form-group mb-4">
                            <label className="font-weight-bold text-secondary mb-2">{t('fileLabel')}</label>
                            <div {...getRootProps()} className="dropzone-box">
                                <input {...getInputProps()} />

                                {acceptedFiles.length > 0 ? (
                                    <div className="py-2">
                                        {acceptedFiles[0].name.toLowerCase().endsWith(".docx") ? (
                                            <i className="fas fa-3x fa-file-word text-primary mb-2"></i>
                                        ) : (
                                            <i className="fas fa-3x fa-file-code text-success mb-2"></i>
                                        )}
                                        <div className="font-weight-bold text-dark">{acceptedFiles[0].name}</div>
                                        <div className="text-muted small">
                                            {(acceptedFiles[0].size / 1024 / 1024).toFixed(2)} MB
                                        </div>
                                        <span className="badge badge-success mt-2">{t('fileSelected')}</span>
                                    </div>
                                ) : (
                                    <div className="py-4">
                                        <i className="fas fa-3x fa-cloud-upload-alt text-muted mb-2"></i>
                                        <div className="font-weight-bold text-dark">{t('dropzonePrompt')}</div>
                                        <div className="text-muted small mt-1">{t('dropzoneClick')}</div>
                                        <div className="badge badge-light border mt-3">{t('dropzoneFormats')}</div>
                                    </div>
                                )}
                            </div>
                        </div>

                        <button
                            type="submit"
                            className={`btn btn-primary btn-lg btn-block ${acceptedFiles.length === 0 ? 'disabled' : ''}`}
                            disabled={acceptedFiles.length === 0}
                        >
                            <i className="fas fa-search mr-2"></i> {t('scanButton')}
                        </button>
                    </form>
                )}

                {mismatch ? (
                    <TemplateMismatchDialog
                        mismatch={mismatch}
                        onCancel={() => setMismatch(null)}
                        onChoose={(template) => {
                            setMismatch(null);
                            setSelectedTemplate(template);
                            void scan(mismatch.file, template, false);
                        }}
                    />
                ) : null}

                {upload === "processing" && (
                    <div className="card shadow-sm border-0 p-4 p-md-5 text-center my-4">
                        <h3 className="h5 font-weight-bold text-primary mb-3">
                            <i className="fas fa-spinner fa-spin mr-2"></i> {t('processingTitle')}
                        </h3>
                        <div className="progress mb-3" style={{ height: '16px' }}>
                            <div
                                className="progress-bar progress-bar-striped progress-bar-animated bg-primary"
                                style={{ width: `${progress > 0 ? progress : 100}%` }}
                            >
                                {progress > 0 ? `${progress}%` : ''}
                            </div>
                        </div>
                        <p className="text-muted small mb-0">
                            {t('processingDesc')}
                        </p>
                    </div>
                )}

                {upload === "error" && (
                    <div className="card shadow-sm border-0 p-4 p-md-5 mb-4">
                        <div className="alert alert-danger d-flex align-items-start mb-4">
                            <i className="fas fa-exclamation-triangle fa-2x mr-3 mt-1"></i>
                            <div>
                                <h5 className="alert-heading font-weight-bold mb-1">{t('errorTitle')}</h5>
                                <div className="small">
                                    {error.split('\n').map((item, key) => (
                                        <div key={key}>{item}</div>
                                    ))}
                                </div>
                            </div>
                        </div>

                        <div className="text-center">
                            <button className="btn btn-primary px-4" onClick={() => restart()}>
                                <i className="fas fa-arrow-left mr-2"></i> {t('retryButton')}
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default Upload;
