"""Modern Windows 11-inspired Dark & Light stylesheets for FontVault."""

from __future__ import annotations


DARK_STYLESHEET = """
QMainWindow, QWidget {
    background-color: #0F172A;
    color: #E2E8F0;
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 13px;
}

QFrame#Sidebar {
    background-color: #0B1120;
    border-right: 1px solid #1E293B;
}

QFrame#TopBar {
    background-color: #111827;
    border-bottom: 1px solid #1E293B;
}

QFrame#FontCard {
    background-color: #1E293B;
    border: 1px solid #334155;
    border-radius: 10px;
}

QFrame#FontCard:hover {
    border: 1px solid #6366F1;
    background-color: #243247;
}

QFrame#FontCard[selected="true"] {
    border: 2px solid #22D3EE;
    background-color: #1E293B;
}

QFrame#PreviewPanel {
    background-color: #111827;
    border-left: 1px solid #1E293B;
}

QFrame#SpecimenBox {
    background-color: #0B1120;
    border: 1px solid #334155;
    border-radius: 8px;
}

QFrame#BatchBar {
    background-color: #111827;
    border: 1px solid #334155;
    border-radius: 8px;
}

QFrame#DividerLine {
    color: #1E293B;
    background-color: #1E293B;
}

QLabel#BrandTitle {
    font-size: 20px;
    font-weight: 800;
    color: #F8FAFC;
    background: transparent;
    padding-left: 6px;
}

QLabel#BrandSub {
    font-size: 11px;
    color: #38BDF8;
    background: transparent;
    padding-left: 6px;
    margin-bottom: 6px;
}

QLabel#CardTitle {
    font-weight: 600;
    font-size: 13px;
    color: #F8FAFC;
    background: transparent;
}

QLabel#CardSpecimen {
    background-color: #0F172A;
    border-radius: 6px;
    padding: 6px 10px;
    color: #F1F5F9;
}

QLabel#PanelTitle {
    font-size: 18px;
    font-weight: 700;
    color: #F8FAFC;
    background: transparent;
}

QLabel#MutedText {
    color: #94A3B8;
    font-size: 11px;
    background: transparent;
}

QLabel#CountLabel {
    color: #94A3B8;
    font-weight: 600;
    background: transparent;
}

QLabel#SizeLabel {
    color: #CBD5E1;
    font-weight: 600;
    background: transparent;
}

QLabel#MainSpecimen {
    color: #F8FAFC;
    background: transparent;
}

QLabel#WaterfallPt {
    color: #64748B;
    font-size: 10px;
    background: transparent;
}

QLabel#WaterfallSample {
    color: #E2E8F0;
    background: transparent;
}

QPushButton {
    background-color: #1E293B;
    color: #E2E8F0;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 6px 12px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #334155;
    border-color: #475569;
}

QPushButton:pressed {
    background-color: #0F172A;
}

QPushButton#ThemeBtn {
    background-color: #1E293B;
    color: #F8FAFC;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 6px 10px;
    font-weight: 600;
    text-align: left;
}

QPushButton#ThemeBtn:hover {
    background-color: #334155;
    border-color: #6366F1;
}

QPushButton#PrimaryBtn {
    background-color: #4F46E5;
    border: 1px solid #6366F1;
    color: #FFFFFF;
    font-weight: 600;
}

QPushButton#PrimaryBtn:hover {
    background-color: #6366F1;
}

QPushButton#AccentBtn {
    background-color: #0891B2;
    border: 1px solid #06B6D4;
    color: #FFFFFF;
    font-weight: 600;
}

QPushButton#AccentBtn:hover {
    background-color: #06B6D4;
}

QPushButton#DangerBtn {
    background-color: #991B1B;
    border: 1px solid #DC2626;
    color: #FFFFFF;
    font-weight: 600;
}

QPushButton#DangerBtn:hover {
    background-color: #B91C1C;
}

QPushButton:disabled {
    opacity: 0.45;
    background-color: #0F172A;
    color: #64748B;
    border-color: #1E293B;
}

QPushButton#NavBtn {
    text-align: left;
    padding: 9px 12px;
    border-radius: 7px;
    border: 1px solid transparent;
    background-color: transparent;
    color: #CBD5E1;
}

QPushButton#NavBtn:hover {
    background-color: #1E293B;
}

QPushButton#NavBtn:checked {
    background-color: #312E81;
    border-color: #4F46E5;
    color: #FFFFFF;
    font-weight: 600;
}

QLineEdit, QPlainTextEdit, QComboBox {
    background-color: #0B1120;
    color: #F8FAFC;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 6px 10px;
}

QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus {
    border-color: #6366F1;
}

QLabel#Badge {
    background-color: #312E81;
    color: #C7D2FE;
    border-radius: 4px;
    padding: 2px 7px;
    font-size: 11px;
    font-weight: 600;
}

QLabel#FormatBadge {
    background-color: #0F172A;
    color: #67E8F9;
    border: 1px solid #164E63;
    border-radius: 4px;
    padding: 2px 6px;
    font-size: 11px;
    font-weight: 600;
}

QLabel#SectionHeader {
    color: #94A3B8;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    background: transparent;
}

QScrollArea {
    border: none;
    background-color: transparent;
}

QScrollBar:vertical {
    background: #0F172A;
    width: 10px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background: #334155;
    min-height: 24px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background: #475569;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QStatusBar {
    background-color: #0B1120;
    color: #94A3B8;
    border-top: 1px solid #1E293B;
}
"""


LIGHT_STYLESHEET = """
QMainWindow, QWidget {
    background-color: #F1F5F9;
    color: #0F172A;
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 13px;
}

QFrame#Sidebar {
    background-color: #FFFFFF;
    border-right: 1px solid #CBD5E1;
}

QFrame#TopBar {
    background-color: #F8FAFC;
    border-bottom: 1px solid #CBD5E1;
}

QFrame#FontCard {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 10px;
}

QFrame#FontCard:hover {
    border: 1px solid #4F46E5;
    background-color: #F8FAFC;
}

QFrame#FontCard[selected="true"] {
    border: 2px solid #0891B2;
    background-color: #F0F9FF;
}

QFrame#PreviewPanel {
    background-color: #FFFFFF;
    border-left: 1px solid #CBD5E1;
}

QFrame#SpecimenBox {
    background-color: #F8FAFC;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
}

QFrame#BatchBar {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
}

QFrame#DividerLine {
    color: #E2E8F0;
    background-color: #E2E8F0;
}

QLabel#BrandTitle {
    font-size: 20px;
    font-weight: 800;
    color: #0F172A;
    background: transparent;
    padding-left: 6px;
}

QLabel#BrandSub {
    font-size: 11px;
    color: #0284C7;
    background: transparent;
    padding-left: 6px;
    margin-bottom: 6px;
}

QLabel#CardTitle {
    font-weight: 600;
    font-size: 13px;
    color: #0F172A;
    background: transparent;
}

QLabel#CardSpecimen {
    background-color: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 6px;
    padding: 6px 10px;
    color: #0F172A;
}

QLabel#PanelTitle {
    font-size: 18px;
    font-weight: 700;
    color: #0F172A;
    background: transparent;
}

QLabel#MutedText {
    color: #475569;
    font-size: 11px;
    background: transparent;
}

QLabel#CountLabel {
    color: #475569;
    font-weight: 600;
    background: transparent;
}

QLabel#SizeLabel {
    color: #334155;
    font-weight: 600;
    background: transparent;
}

QLabel#MainSpecimen {
    color: #0F172A;
    background: transparent;
}

QLabel#WaterfallPt {
    color: #64748B;
    font-size: 10px;
    background: transparent;
}

QLabel#WaterfallSample {
    color: #1E293B;
    background: transparent;
}

QPushButton {
    background-color: #F8FAFC;
    color: #0F172A;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 6px 12px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #E2E8F0;
    border-color: #94A3B8;
}

QPushButton:pressed {
    background-color: #CBD5E1;
}

QPushButton#ThemeBtn {
    background-color: #EEF2FF;
    color: #312E81;
    border: 1px solid #C7D2FE;
    border-radius: 6px;
    padding: 6px 10px;
    font-weight: 600;
    text-align: left;
}

QPushButton#ThemeBtn:hover {
    background-color: #E0E7FF;
    border-color: #6366F1;
}

QPushButton#PrimaryBtn {
    background-color: #4F46E5;
    border: 1px solid #4338CA;
    color: #FFFFFF;
    font-weight: 600;
}

QPushButton#PrimaryBtn:hover {
    background-color: #4338CA;
}

QPushButton#AccentBtn {
    background-color: #0891B2;
    border: 1px solid #0E7490;
    color: #FFFFFF;
    font-weight: 600;
}

QPushButton#AccentBtn:hover {
    background-color: #0E7490;
}

QPushButton#DangerBtn {
    background-color: #DC2626;
    border: 1px solid #B91C1C;
    color: #FFFFFF;
    font-weight: 600;
}

QPushButton#DangerBtn:hover {
    background-color: #B91C1C;
}

QPushButton:disabled {
    background-color: #E2E8F0;
    color: #94A3B8;
    border-color: #CBD5E1;
}

QPushButton#NavBtn {
    text-align: left;
    padding: 9px 12px;
    border-radius: 7px;
    border: 1px solid transparent;
    background-color: transparent;
    color: #334155;
}

QPushButton#NavBtn:hover {
    background-color: #F1F5F9;
}

QPushButton#NavBtn:checked {
    background-color: #E0E7FF;
    border-color: #6366F1;
    color: #312E81;
    font-weight: 600;
}

QLineEdit, QPlainTextEdit, QComboBox {
    background-color: #FFFFFF;
    color: #0F172A;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 6px 10px;
}

QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus {
    border-color: #4F46E5;
}

QLabel#Badge {
    background-color: #E0E7FF;
    color: #3730A3;
    border-radius: 4px;
    padding: 2px 7px;
    font-size: 11px;
    font-weight: 600;
}

QLabel#FormatBadge {
    background-color: #ECFEFF;
    color: #0E7490;
    border: 1px solid #A5F3FC;
    border-radius: 4px;
    padding: 2px 6px;
    font-size: 11px;
    font-weight: 600;
}

QLabel#SectionHeader {
    color: #64748B;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    background: transparent;
}

QScrollArea {
    border: none;
    background-color: transparent;
}

QScrollBar:vertical {
    background: #F1F5F9;
    width: 10px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background: #CBD5E1;
    min-height: 24px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background: #94A3B8;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QStatusBar {
    background-color: #FFFFFF;
    color: #475569;
    border-top: 1px solid #CBD5E1;
}
"""


def get_stylesheet(theme: str) -> str:
    """Return QSS stylesheet for 'light' or 'dark' theme mode."""
    return LIGHT_STYLESHEET if str(theme).strip().lower() == "light" else DARK_STYLESHEET
