import React from "react";
import "./Header.css";
import { useLanguage } from "./i18n";

interface HeaderProps {
    onReset?: () => void;
}

const Header: React.FC<HeaderProps> = ({ onReset }) => {
    const { language, setLanguage } = useLanguage();

    return (
        <header className="header">
            <div className="container header-content">
                {/* Left: PASJ Logo + Title */}
                <div 
                    className="header-brand" 
                    onClick={onReset} 
                    style={{ cursor: onReset ? 'pointer' : 'default' }}
                    title={language === 'ja' ? 'ホームに戻る' : 'Return to Home'}
                >
                    <img alt="PASJ Logo" src={"pasj_logo.png"} className="pasj-logo" />
                    <div className="header-divider" />
                    <div className="header-title-group">
                        <h1 className="header-title-main">
                            {language === 'ja' ? '論文原稿の自動フォーマット検証' : 'Automated Paper Formatting Validator'}
                        </h1>
                        <div className="header-title-sub">
                            {language === 'ja' ? 'Automated Paper Formatting Validator' : '論文原稿の自動フォーマット検証'}
                        </div>
                    </div>
                </div>

                {/* Right: Language Switcher */}
                <div className="header-actions">
                    <div className="lang-switcher btn-group btn-group-sm" role="group" aria-label="Language Switcher">
                        <button
                            type="button"
                            className={`btn ${language === 'ja' ? 'btn-primary font-weight-bold' : 'btn-outline-secondary'}`}
                            onClick={() => setLanguage('ja')}
                        >
                            日本語
                        </button>
                        <button
                            type="button"
                            className={`btn ${language === 'en' ? 'btn-primary font-weight-bold' : 'btn-outline-secondary'}`}
                            onClick={() => setLanguage('en')}
                        >
                            English
                        </button>
                    </div>
                </div>
            </div>
        </header>
    );
};

export default Header;