import React from 'react';
import { Accept, useDropzone } from 'react-dropzone';
import api from './api';
import './Upload.css';
import { Report } from "./App";
import { useSearchParams } from "react-router-dom";
import { useLanguage } from "./i18n";

type UploadState = "idle" | "uploading" | "processing" | "success" | "error";
type TemplateChoice = 'auto' | 'pasj' | 'jacow';

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

const Upload: React.FC<UploadProps> = (props) => {
    const { t } = useLanguage();
    const [searchParams, setSearchParams] = useSearchParams();
    const [selectedTemplate, setSelectedTemplate] = React.useState<TemplateChoice>('auto');
    const [progress, setProgress] = React.useState(0);
    const [upload, setUpload] = React.useState<UploadState>('idle');
    const [error, setError] = React.useState<string>('');

    const opts = {
        accept: allowedExtensions,
        multiple: false,
    };

    const applyScanResponse = (data: any, fallbackFilename?: string) => {
        if (data.error && !data.scores) {
            setUpload("error");
            setError(data.error);
            return;
        }
        if (data.report_type === 'latex') {
            setUpload("success");
            props.setReport({
                type: "latex",
                report: {
                    filename: data.filename || fallbackFilename || "document.tex",
                    content: data.body,
                    isAbbreviated: data.isabbreviated,
                    unabbreviated: data.unabbreviated,
                    issuesFound: data.issuesFound,
                    detected_template: data.detected_template,
                    template_name: data.template_name,
                    total_references: data.total_references,
                    issues: data.issues,
                },
            });
        } else {
            setUpload("success");
            props.setReport({ type: "word", report: data });
        }
        if (data.report_id) {
            setSearchParams({ results: data.report_id });
        }
    };

    // Load saved report by ID if present in URL query (?results=...)
    React.useEffect(() => {
        const resultsId = searchParams.get("results");
        if (resultsId) {
            setUpload("processing");
            api.get(`/api/reports/${resultsId}`)
                .then((response) => applyScanResponse(response.data))
                .catch(() => {
                    setUpload("error");
                    setError(t('reportLoadError'));
                });
        }
    }, [searchParams]);

    const restart = () => {
        setProgress(0);
        setUpload('idle');
        setError('');
    };

    const { getRootProps, getInputProps, acceptedFiles } = useDropzone(opts);
    const scanMultipart = (endpoint: string, file: File) => {
        const formData = new FormData();
        formData.append("file", file);
        formData.append("template", selectedTemplate);
        return api.post(endpoint, formData, {
            headers: {
                "Content-Type": "multipart/form-data"
            },
            onUploadProgress: (progressEvent) => {
                if (progressEvent.progress !== undefined) {
                    setProgress(Math.round(progressEvent.progress * 100));
                }
            }
        });
    };

    const uploadLaTeX = async (content: string, template: TemplateChoice) => {
        return api({
            onUploadProgress: (progressEvent) => {
                if (progressEvent.progress !== undefined) {
                    setProgress(Math.round(progressEvent.progress * 100));
                }
            },
            url: "/api/scan/latex",
            method: 'POST',
            data: {
                filename: acceptedFiles[0].name,
                content: content,
                template: template,
            },
            headers: {
                'Content-Type': "application/json"
            },
        });
    };

    const submitForm = async () => {
        try {
            if (acceptedFiles.length > 0) {
                setUpload("uploading");
                const file = acceptedFiles[0];
                const lowerName = file.name.toLowerCase();
                const isDocx = file.type === "application/vnd.openxmlformats-officedocument.wordprocessingml.document" || lowerName.endsWith(".docx");
                const isArchive = lowerName.endsWith(".zip") || lowerName.endsWith(".tar.gz") || lowerName.endsWith(".tgz");

                if (isDocx) {
                    setUpload("processing");
                    const response = await scanMultipart("/api/scan/word", file);
                    applyScanResponse(response.data, file.name);
                } else if (isArchive) {
                    setUpload("processing");
                    const response = await scanMultipart("/api/scan/file", file);
                    applyScanResponse(response.data, file.name);
                } else {
                    const content = await file.text();
                    const response = await uploadLaTeX(content, selectedTemplate);
                    if (response.status !== 200) {
                        setUpload("error");
                        setError(response.data);
                    } else {
                        applyScanResponse(response.data, file.name);
                    }
                }
            }
        } catch (err: any) {
            setUpload("error");
            setError(err.response?.data?.code === 'checker_not_implemented'
                ? t('checkerNotImplemented')
                : err.response?.data?.error || err.message || "An unexpected error occurred during paper validation.");
        }
    };

    return (
        <div className="row justify-content-center my-3">
            <div className="col-lg-8 col-xl-7">
                {upload === 'idle' && (
                    <form onSubmit={(e) => {
                        e.preventDefault();
                        submitForm();
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
                                    className={`btn py-2 ${selectedTemplate === 'auto' ? 'btn-primary font-weight-bold' : 'btn-outline-secondary'}`}
                                    onClick={() => setSelectedTemplate('auto')}
                                    style={{ width: '30%' }}
                                >
                                    <i className="fas fa-magic mr-2"></i> {t('templateAuto')}
                                </button>
                                <button
                                    type="button"
                                    className={`btn py-2 ${selectedTemplate === 'pasj' ? 'btn-primary font-weight-bold' : 'btn-outline-secondary'}`}
                                    onClick={() => setSelectedTemplate('pasj')}
                                    style={{ width: '35%' }}
                                >
                                    <i className="fas fa-file-alt mr-2"></i> {t('templatePasj')}
                                </button>
                                <button
                                    type="button"
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

                {(upload === "uploading" || upload === "processing") && (
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
