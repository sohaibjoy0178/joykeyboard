"""Static pearl-glass surfaces shared by the bar, studio and writing tools."""

WORKSPACE_STYLE = """
QWidget { color:#172337; font-family:'Segoe UI','Nirmala UI'; font-size:14px; font-style:normal; font-weight:400; }
QMainWindow, QWidget#workspaceRoot { background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #F8FAFD,stop:0.55 #EFF3F9,stop:1 #E6EDF7); }
QScrollArea, QScrollArea > QWidget > QWidget, QTabWidget, QTabWidget > QWidget, QLabel { background:transparent; }
QLabel#eyebrow { color:#526279; font-size:11px; font-weight:600; letter-spacing:1px; }
QLabel#title { color:#172337; font-family:'Segoe UI Variable Display','Segoe UI'; font-size:32px; font-weight:600; }
QLabel#muted { color:#526279; }
QLabel#state { color:#172337; font-size:22px; font-weight:600; }
QFrame#panel, QWidget#voiceControls { background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #FFFFFF,stop:1 #F0F5FC); border:1px solid #FFFFFF; border-radius:20px; }
QFrame#panel QLabel, QFrame#panel QCheckBox { background:transparent; border:0; }
QPushButton { background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #FFFFFF,stop:1 #EAF0F8); border:1px solid #CAD5E5; border-radius:12px; padding:10px 17px; font-weight:600; }
QPushButton:hover { background:#FFFFFF; border-color:#7FAAE0; }
QPushButton:pressed { background:#DFE9F6; border-color:#7FAAE0; }
QPushButton:focus { border:2px solid #0068D9; }
QPushButton:disabled { color:#78869A; background:#ECF0F5; border-color:#DBE2EB; }
QPushButton#primary { background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #1A70D2,stop:0.45 #0968D2,stop:1 #005AC2); color:#FFFFFF; border:1px solid #75ACF4; padding:16px; font-size:16px; border-radius:16px; }
QPushButton#primary:hover { background:#1266C8; }
QPushButton#primary:pressed { background:#0055BB; }
QPushButton#primary:disabled { background:#DDE7F4; color:#65778F; border-color:#C9D7E9; }
QPushButton#cancel { color:#AE2638; }
QPushButton#cancel:disabled { color:#78869A; }
QComboBox { background:#FAFCFF; border:1px solid #CBD5E3; border-radius:11px; padding:9px 12px; min-height:23px; font-family:'Nirmala UI','Segoe UI'; }
QComboBox:hover, QComboBox:focus { border-color:#448ADF; }
QComboBox:disabled { color:#78869A; background:#EDF1F6; }
QComboBox::drop-down { border:0; width:25px; }
QComboBox QAbstractItemView { background:#FAFCFF; color:#172337; selection-background-color:#DDEBFF; selection-color:#123C73; padding:8px; outline:0; }
QCheckBox { spacing:9px; padding:5px 0; background:transparent; font-family:'Nirmala UI','Segoe UI'; }
QCheckBox::indicator { width:17px; height:17px; border:1px solid #A8B8CE; border-radius:6px; background:#FFFFFF; }
QCheckBox::indicator:checked { background:#0068D9; border:3px solid #B3D5FF; }
QCheckBox::indicator:disabled { background:#DDE3EB; border-color:#C4CEDC; }
QCheckBox:focus { outline:1px solid #0068D9; }
QPlainTextEdit, QLineEdit, QKeySequenceEdit { background:#FCFDFF; color:#172337; placeholder-text-color:#526279; border:1px solid #CBD5E3; border-radius:14px; padding:12px; selection-background-color:#C7DFFF; selection-color:#102E58; }
QPlainTextEdit { padding:16px; font-size:16px; font-family:'Nirmala UI','Segoe UI'; }
QPlainTextEdit:focus, QLineEdit:focus, QKeySequenceEdit:focus { border-color:#0068D9; }
QKeySequenceEdit QLineEdit { background:transparent; border:0; padding:2px; }
QProgressBar { border:0; border-radius:3px; background:#DCE5F1; max-height:6px; min-height:6px; }
QProgressBar::chunk { background:#0068D9; border-radius:3px; }
QTabWidget::pane { border:0; background:transparent; }
QTabBar { background:#E5EBF3; border-radius:14px; }
QTabBar::tab { background:transparent; color:#526279; padding:11px 18px; margin:3px; border:1px solid transparent; border-radius:11px; }
QTabBar::tab:selected { background:#FFFFFF; color:#12519C; border:1px solid #D0DCEB; font-weight:600; }
QTabBar::tab:hover:!selected { background:#F0F5FC; }
QMenu { background:#F7FAFF; color:#172337; border:1px solid #C4D1E3; padding:7px; border-radius:12px; }
QMenu::item { padding:9px 24px; border-radius:7px; }
QMenu::item:selected { background:#DDEBFF; color:#123C73; }
QMenu::separator { height:1px; background:#D8E1EE; margin:6px 10px; }
QToolTip { background:#F8FAFF; color:#172337; border:1px solid #BCCCE0; padding:8px; }
QScrollBar:vertical { background:#E9EEF5; width:10px; border-radius:5px; margin:2px; }
QScrollBar::handle:vertical { background:#B6C4D7; border-radius:4px; min-height:28px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background:transparent; }
"""

BAR_STYLE = """
QWidget { color:#172337; font-family:'Segoe UI','Nirmala UI'; font-size:12px; font-style:normal; font-weight:400; }
QWidget#floatingRoot, QFrame#shell, QLabel { background:transparent; border:0; }
QToolButton { background:transparent; border:1px solid transparent; border-radius:10px; padding:4px; }
QToolButton:hover { background:#FFFFFF; border:1px solid #C5D6EA; }
QToolButton:pressed { background:#DFE9F7; }
QToolButton:disabled { color:#7C8A9D; }
QToolButton#brand { padding:0; }
QToolButton#mode { color:#34465F; font-size:12px; font-family:'Nirmala UI','Segoe UI'; }
QToolButton#keyboard[active="true"] { background:#DAEAFF; border:1px solid #9CC2F3; }
QToolButton#speak { color:#FFFFFF; background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #1A70D2,stop:0.45 #0C66CD,stop:1 #005ABF); border:1px solid #8ABAF5; font-weight:600; border-radius:11px; }
QToolButton#speak:hover { background:#1266C8; border-color:#B2D5FF; }
QToolButton#speak:pressed { background:#0058BC; }
QToolButton#speak[recording="true"] { background:#FCE7EA; border-color:#DBA1AC; color:#982638; }
QToolButton#speak:disabled { background:#DFE9F6; border-color:#C1D2E8; color:#607591; }
QToolButton#candidate { background:#F5F9FF; border:1px solid #C9D9EC; border-radius:8px; padding:2px 5px; text-align:left; font-family:'Nirmala UI','Segoe UI'; }
QToolButton#candidate:hover { background:#DEECFF; border-color:#6EA6EC; }
QLabel#composition { color:#095CBF; font-size:13px; font-family:'Nirmala UI','Segoe UI'; }
QLabel#status { color:#455A76; font-size:11px; }
QLabel#status[error="true"] { color:#AE2638; }
QProgressBar { background:#CCD9EB; border:0; border-radius:2px; max-height:3px; min-height:3px; }
QProgressBar::chunk { background:#0068D9; border-radius:2px; }
QMenu { background:#F5F9FF; color:#172337; border:1px solid #BBCDE4; padding:7px; border-radius:12px; font-family:'Segoe UI'; font-size:13px; }
QMenu::item { padding:8px 28px 8px 19px; border-radius:7px; }
QMenu::item:selected { background:#DCEAFF; color:#123C73; }
QMenu::item:disabled { color:#71839C; }
QMenu::separator { background:#D2DEEF; height:1px; margin:6px 10px; }
QToolTip { background:#F8FAFF; color:#172337; border:1px solid #BCCCE0; padding:7px; }
"""

TOOLS_STYLE = """
QLineEdit, QListWidget { background:#FCFDFF; color:#172337; border:1px solid #CBD5E3;
    border-radius:12px; padding:8px; selection-background-color:#DDEBFF; selection-color:#123C73; font-family:'Nirmala UI','Segoe UI'; }
QLineEdit:focus, QListWidget:focus { border:1px solid #0068D9; }
QListWidget::item { padding:4px; border-radius:6px; }
QListWidget::item:selected { background:#DDEBFF; color:#123C73; }
QCheckBox { color:#172337; spacing:8px; background:transparent; }
QCheckBox::indicator { width:18px; height:18px; border:1px solid #A8B8CE; border-radius:6px; background:#FFFFFF; }
QCheckBox::indicator:checked { background:#0068D9; border:3px solid #B3D5FF; }
QCheckBox:focus { outline:1px solid #0068D9; }
"""
