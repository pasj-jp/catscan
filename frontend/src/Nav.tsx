import React from 'react';
import { Pages } from "./App";
import './Nav.css';
import { useLanguage } from "./i18n";

type NavProps = {
    page: Pages,
    changePage: (page: Pages) => void
}

const Nav: React.FC<NavProps> = (props) => {
    const { t } = useLanguage();

    return (
        <div className="nav-area">
            <div className="container">
                <nav className="navbar navbar-expand">
                    <ul className="navbar-nav mr-auto">
                        <li className={`nav-item ${props.page === Pages.Upload ? "active" : ""}`}>
                            <button onClick={() => props.changePage(Pages.Upload)} className="nav-link nav-btn"
                                    type="button">
                                <i className="fas fa-check-circle mr-1"></i> {t('navValidator')}
                            </button>
                        </li>
                        <li className={`nav-item ${props.page === Pages.Resources ? "active" : ""}`}>
                            <button onClick={() => props.changePage(Pages.Resources)}
                                    className="nav-link nav-btn"
                                    type="button">
                                <i className="fas fa-file-alt mr-1"></i> {t('navResources')}
                            </button>
                        </li>
                    </ul>
                </nav>
            </div>
        </div>
    );
};

export default Nav;
