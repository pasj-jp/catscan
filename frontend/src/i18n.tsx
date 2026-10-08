import React, { createContext, useContext, useState } from 'react';

export type Language = 'ja' | 'en';

export const translations = {
    ja: {
        // Header
        orgName: '日本加速器学会',
        orgSub: 'Particle Accelerator Society of Japan',
        appTitle: 'PASJ CatScan',
        appSub: '論文フォーマット検証システム',
        
        // Navigation
        navValidator: '論文検証',
        navResources: '執筆要領・テンプレート',

        // Upload Form (Ultra clean)
        uploadTitle: '原稿ファイルのアップロード',
        uploadSubtitle: '日本加速器学会 (PASJ) 年会プロシーディングス原稿 (.docx / .tex) を選択してください。',
        templateLabel: '原稿フォーマット種別:',
        templateJacow: 'JACoW 英文原稿 (English)',
        templateJacowName: 'JACoW 英文原稿',
        templateJacowDesc: 'JACoW公式フォーマット（英語執筆）の余白・見出し・スタイル・参考文献を検査します。',
        templatePasj: 'PASJ 和文原稿 (Japanese)',
        templatePasjName: 'PASJ 和文原稿',
        templatePasjDesc: 'PASJ 和文原稿の検査機能は準備中です。',
        checkerNotImplemented: 'この原稿形式の検査機能はまだ実装されていません。',
        fileLabel: '原稿ファイル (.docx または .tex):',
        dropzonePrompt: 'ここに原稿ファイルをドラッグ＆ドロップ',
        dropzoneClick: 'またはクリックしてファイルを選択',
        dropzoneFormats: '対応形式: .docx (Microsoft Word) / .tex (LaTeX)',
        fileSelected: 'ファイル選択済み（クリックで変更）',
        scanButton: 'フォーマットを検査する (Scan Paper)',

        // Processing
        processingTitle: '論文を解析しています...',
        processingDesc: 'スタイル設定、ページ余白、段組み、図表キャプション、参考文献形式を検証しています。',
        errorTitle: '検証に失敗しました',
        retryButton: '戻って再試行',

        // Resources Page (Holds all detailed checklists & templates)
        resourcesTitle: '論文執筆案内・公式テンプレート',
        pasjSection: '日本加速器学会 (PASJ) 年会論文',
        pasjDesc: '最新の年会プロシーディングス原稿用テンプレートです。日本語、英語ともA4サイズ2～5ページで執筆してください。',
        wordTemplate: 'Word テンプレート (.dotx)',
        wordSample: 'Word 原稿作成案内 (兼PDF作成サンプル)',
        texTemplate: 'TeX テンプレート (.zip / LuaLaTeX & upLaTeX)',
        pasjOfficialPage: 'PASJ 公式プロシーディングステンプレート案内ページ',
        pasjEnglishNote: '※ 全て英語で原稿を執筆する場合には、JACoWの公式テンプレートをご利用ください。',
        
        // Checklist (displayed inside Resources page)
        pasjChecklistTitle: '年会プロシーディングス執筆の重要チェック項目',
        checkA4: 'A4サイズ 2～5ページ（原稿末尾の参考文献リストのみ6ページ目以降にまたがっても可）',
        checkTemplate: '古いテンプレートの使用は避け、必ず最新の公式テンプレートを使用すること',
        checkBilingual: '和文原稿の場合、タイトルおよび著者名は日本語と英語を併記（区切りは半角カンマ「, 」）',
        checkPunctuation: '日本語の文章は句読点（「。」と「、」）を使って記述（「，」「．」は避ける）',
        checkCaptions: '図表とその説明文（キャプション）は原則英語で記述（Figure, Table と記して参照）',
        checkSpacing: '数値と単位記号の間は詰めず、スペース（不間断スペース）を挿入（例: 10 MeV）',
        checkFonts: '文字化け防止のため、PDFファイルはできるだけ全てのフォントを埋め込んで作成すること',

        jacowSection: 'JACoW 国際会議論文 (English Papers)',
        jacowDesc: 'JACoW (Joint Accelerator Conferences Website) 共通テンプレートおよび引用・フォーマット規約です。',
        jacowWord: 'JACoW Word Templates',
        jacowLatex: 'JACoW LaTeX Templates',
        jacowCitations: 'Citation & References Formatting Guide',
        jacowHelp: 'CatScan Validator Help & Diagnostics Guide',
        aboutNote: '本システムは日本加速器学会専用の論文フォーマット自動検証システムです。自前サーバ上で安全に処理されます。',

        // Word Report
        reportTitle: '検証レポート',
        guidelineHelp: 'JACoW 診断ヘルプガイド',
        pasjGuidelines: 'PASJ 年会プロシーディングス要領',
        scoreSummary: '総合判定スコア',
        scoreOk: '適合',
        scoreWarnings: '警告',
        scoreErrors: 'エラー',
        overall: '全体スコア',
        backToUpload: '新しい原稿を検証する',
        latexNoIssues: '参考文献やフォーマット上の問題は検出されませんでした（適合）。',
        latexIssuesDetected: '参考文献（References）に以下の要修正項目が検出されました:',
        latexIssueCount: '検出された問題件数',
    },
    en: {
        // Header
        orgName: 'Particle Accelerator Society of Japan',
        orgSub: '日本加速器学会',
        appTitle: 'PASJ CatScan',
        appSub: 'Paper Formatting Validator',
        
        // Navigation
        navValidator: 'Validator',
        navResources: 'Guidelines & Templates',

        // Upload Form (Ultra clean)
        uploadTitle: 'Upload Manuscript',
        uploadSubtitle: 'Upload your PASJ conference manuscript (.docx or .tex) for automated formatting checks.',
        templateLabel: 'Manuscript Format:',
        templateJacow: 'JACoW English Paper',
        templateJacowName: 'JACoW English Paper',
        templateJacowDesc: 'Verifies margins, styles, headings, and references for JACoW format (English papers).',
        templatePasj: 'PASJ Japanese Paper',
        templatePasjName: 'PASJ Japanese Paper',
        templatePasjDesc: 'PASJ Japanese manuscript validation is not implemented yet.',
        checkerNotImplemented: 'Validation for this manuscript format is not implemented yet.',
        fileLabel: 'Paper File (.docx or .tex):',
        dropzonePrompt: 'Drag & drop your paper here',
        dropzoneClick: 'or click to browse from your computer',
        dropzoneFormats: 'Supported formats: .docx (Microsoft Word) / .tex (LaTeX)',
        fileSelected: 'File selected (click to change)',
        scanButton: 'Scan Paper',

        // Processing
        processingTitle: 'Analyzing Document...',
        processingDesc: 'Verifying styles, page margins, columns, captions, and reference formatting.',
        errorTitle: 'Validation Failed',
        retryButton: 'Back to Try Again',

        // Resources Page
        resourcesTitle: 'Paper Guidelines & Official Templates',
        pasjSection: 'PASJ Annual Meeting Papers (Japanese & English)',
        pasjDesc: 'Official templates for PASJ conferences. Manuscripts must be A4, 2-5 pages in length.',
        wordTemplate: 'Word Template (.dotx)',
        wordSample: 'Word Author Guide (Sample PDF)',
        texTemplate: 'TeX Template (.zip / LuaLaTeX & upLaTeX)',
        pasjOfficialPage: 'PASJ Official Templates Webpage',
        pasjEnglishNote: 'Note: For papers written entirely in English, please use the JACoW official templates directly.',

        // Checklist (displayed inside Resources page)
        pasjChecklistTitle: 'PASJ Manuscript Preparation Checklist',
        checkA4: 'A4 paper size, 2 to 5 pages (only the references list may extend to page 6+)',
        checkTemplate: 'Avoid outdated templates; always use the latest official template',
        checkBilingual: 'For Japanese papers: Title and author names must be bilingual (Japanese and English)',
        checkPunctuation: 'For Japanese text: Use standard Japanese punctuation marks 「。」 and 「、」',
        checkCaptions: 'Figures, tables, and their captions must be written in English (Figure, Table)',
        checkSpacing: 'Insert a space (non-breaking space) between numbers and unit symbols (e.g. 10 MeV)',
        checkFonts: 'Embed all fonts when converting to PDF to prevent character corruption',

        jacowSection: 'JACoW Conference Papers (English Papers)',
        jacowDesc: 'Templates and citation formatting specifications from the JACoW collaboration.',
        jacowWord: 'JACoW Word Templates',
        jacowLatex: 'JACoW LaTeX Templates',
        jacowCitations: 'Citation & References Formatting Guide',
        jacowHelp: 'CatScan Validator Help & Diagnostics Guide',
        aboutNote: 'This system is dedicated to PASJ conference paper validation and operates on on-premise servers.',

        // Word Report
        reportTitle: 'Validation Report',
        guidelineHelp: 'JACoW Diagnostic Help Guide',
        pasjGuidelines: 'PASJ Conference Guidelines',
        scoreSummary: 'Score Breakdown',
        scoreOk: 'OK',
        scoreWarnings: 'Warnings',
        scoreErrors: 'Errors',
        overall: 'Overall',
        backToUpload: 'Scan Another Paper',
        latexNoIssues: 'No issues found in paper references (Conforms to JACoW standards).',
        latexIssuesDetected: 'The following formatting issues were detected in your references:',
        latexIssueCount: 'Issues Found',
    }
};

type Translations = typeof translations.ja;

interface LanguageContextType {
    language: Language;
    setLanguage: (lang: Language) => void;
    t: (key: keyof Translations) => string;
}

const LanguageContext = createContext<LanguageContextType>({
    language: 'ja',
    setLanguage: () => {},
    t: (key) => translations.ja[key] || String(key),
});

export const LanguageProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [language, setLanguageState] = useState<Language>(() => {
        const saved = localStorage.getItem('pasj_catscan_lang');
        return (saved === 'en' || saved === 'ja') ? saved : 'ja';
    });

    const setLanguage = (lang: Language) => {
        setLanguageState(lang);
        localStorage.setItem('pasj_catscan_lang', lang);
    };

    const t = (key: keyof Translations): string => {
        return translations[language][key] || translations['ja'][key] || String(key);
    };

    return (
        <LanguageContext.Provider value={{ language, setLanguage, t }}>
            {children}
        </LanguageContext.Provider>
    );
};

export const useLanguage = () => useContext(LanguageContext);
