"""Modern Windows 11-inspired dark stylesheet for FontVault."""

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
