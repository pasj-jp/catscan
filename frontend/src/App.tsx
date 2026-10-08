import React from 'react';
import { useSearchParams } from 'react-router-dom';
import 'bootstrap/dist/css/bootstrap.css';
import './App.css';
import Word, { WordReport } from "./Word/Word";
import LaTeX, { LaTeXReport } from "./LaTeX/LaTeX";
import Nav from "./Nav";
import Resources from "./Resources/Resources";
import Header from "./Header";
import Upload from "./Upload";
import { LanguageProvider } from "./i18n";

enum Pages {
    Upload,
    Resources
}

type ReportType = "word" | "latex";

type Report = {
    type: ReportType,
    report: WordReport | LaTeXReport
};

interface ErrorBoundaryProps {
    children: React.ReactNode;
}

interface ErrorBoundaryState {
    hasError: boolean;
    error?: Error;
}

class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
    constructor(props: ErrorBoundaryProps) {
        super(props);
        this.state = { hasError: false };
    }

    static getDerivedStateFromError(error: Error): ErrorBoundaryState {
        return { hasError: true, error };
    }

    componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
        console.error("ErrorBoundary caught an error:", error, errorInfo);
    }

    render() {
        if (this.state.hasError) {
            return (
                <div className="container py-5 text-center">
                    <div className="card shadow-sm border-0 p-5 mx-auto" style={{ maxWidth: '600px' }}>
                        <i className="fas fa-exclamation-triangle fa-3x text-danger mb-3"></i>
                        <h4 className="font-weight-bold text-dark mb-2">表示エラーが発生しました</h4>
                        <p className="text-muted small mb-4">
                            {this.state.error?.message || "予期しないエラーが発生しました。"}
                        </p>
                        <div>
                            <button 
                                className="btn btn-primary px-4"
                                onClick={() => {
                                    this.setState({ hasError: false });
                                    window.location.href = window.location.pathname;
                                }}
                            >
                                ホームに戻る (Return to Home)
                            </button>
                        </div>
                    </div>
                </div>
            );
        }

        return this.props.children;
    }
}

function MainContent() {
    const [report, setReport] = React.useState<Report | null>(null);
    const [page, setPage] = React.useState<Pages>(Pages.Upload);
    const [searchParams, setSearchParams] = useSearchParams();

    const resetReport = () => {
        setReport(null);
        if (searchParams.has('results')) {
            const nextParams = new URLSearchParams(searchParams);
            nextParams.delete('results');
            setSearchParams(nextParams);
        }
    };

    const changePage = (newPage: Pages) => {
        resetReport();
        setPage(newPage);
    };

    return (
        <div>
            <Header onReset={() => { resetReport(); setPage(Pages.Upload); }} />
            <Nav page={page} changePage={changePage} />
            <div className="container pb-5">
                {page === Pages.Upload && report === null && <Upload setReport={setReport} />}
                {page === Pages.Upload && report !== null && report.type === 'word' && (
                    <Word report={report.report as WordReport} onReset={resetReport} />
                )}
                {page === Pages.Upload && report !== null && report.type === 'latex' && (
                    <LaTeX report={report.report as LaTeXReport} onReset={resetReport} />
                )}
                {page === Pages.Resources && <Resources />}
            </div>
        </div>
    );
}

function App() {
    return (
        <LanguageProvider>
            <ErrorBoundary>
                <MainContent />
            </ErrorBoundary>
        </LanguageProvider>
    );
}

export type { Report };
export { Pages };
export default App;
