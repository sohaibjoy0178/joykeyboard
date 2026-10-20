"""Transparent light and dark glass surfaces shared by the bar, studio and writing tools."""

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

GLASS_WORKSPACE = """
QMainWindow, QWidget#workspaceRoot { background:transparent; }
QLabel#eyebrow, QLabel#muted { color:#172337; }
QFrame#panel, QWidget#voiceControls { background:rgba(255,255,255,82); border-color:rgba(255,255,255,170); }
QPushButton { background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 rgba(255,255,255,155),stop:1 rgba(244,249,255,65)); border-color:rgba(255,255,255,190); }
QPushButton:hover { background:rgba(255,255,255,205); border-color:#FFFFFF; }
QPushButton:pressed { background:rgba(215,233,255,180); }
QPushButton:disabled { color:#586A80; background:rgba(244,249,255,90); border-color:rgba(255,255,255,100); }
QPushButton#primary { border-color:rgba(255,255,255,200); }
QPushButton#primary:disabled { background:rgba(220,232,248,155); color:#52647D; }
QComboBox { background:rgba(255,255,255,155); border-color:rgba(255,255,255,190); }
QComboBox:disabled { background:rgba(240,247,255,120); }
QPlainTextEdit, QLineEdit, QKeySequenceEdit { background:rgba(255,255,255,155); border-color:rgba(255,255,255,190); }
QKeySequenceEdit QLineEdit { background:transparent; }
QTabBar { background:rgba(255,255,255,38); }
QTabBar::tab { color:#263950; }
QTabBar::tab:selected { background:rgba(255,255,255,175); border-color:rgba(255,255,255,225); }
QTabBar::tab:hover:!selected { background:rgba(255,255,255,95); }
QScrollBar:vertical { background:rgba(255,255,255,45); }
QScrollBar::handle:vertical { background:rgba(61,85,116,110); }
QSizeGrip { background:transparent; width:15px; height:15px; }
"""

GLASS_BAR = """
QToolButton#mode { color:#172337; }
QToolButton:hover { background:rgba(255,255,255,155); border-color:rgba(255,255,255,210); }
QToolButton:pressed { background:rgba(213,231,255,160); }
QToolButton#keyboard[active="true"] { background:rgba(202,226,255,195); border-color:rgba(255,255,255,205); }
QToolButton#candidate { background:rgba(255,255,255,160); border-color:rgba(255,255,255,205); }
QToolButton#candidate:hover { background:rgba(224,238,255,225); }
QLabel#status { color:#172337; }
"""

GLASS_TOOLS = """
QLineEdit, QListWidget { background:rgba(255,255,255,155); border-color:rgba(255,255,255,190); }
"""

DARK_WORKSPACE = """
QWidget { color:#EDF2FA; }
QLabel#title, QLabel#state { color:#EDF2FA; }
QLabel#eyebrow, QLabel#muted { color:#EDF2FA; }
QFrame#panel, QWidget#voiceControls { background:rgba(8,13,21,55); border-color:rgba(255,255,255,70); }
QPushButton { color:#EDF2FA; background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 rgba(255,255,255,35),stop:1 rgba(8,13,21,55)); border-color:rgba(255,255,255,85); }
QPushButton:hover { background:rgba(59,70,86,120); border-color:#739BD1; }
QPushButton:pressed { background:rgba(27,37,51,120); }
QPushButton:disabled { color:#8592A5; background:rgba(35,40,50,120); border-color:#343E4D; }
QPushButton#primary { color:#FFFFFF; border-color:#75ACF4; }
QPushButton#primary:disabled { background:rgba(38,51,68,120); color:#94A5BD; border-color:#40536D; }
QPushButton#cancel { color:#FFABB8; }
QPushButton#cancel:disabled { color:#8592A5; }
QComboBox { color:#EDF2FA; background:rgba(28,32,39,120); border-color:#4A5668; }
QComboBox:disabled { color:#8592A5; background:rgba(35,40,50,120); }
QComboBox QAbstractItemView { background:rgba(34,40,50,120); color:#EDF2FA; selection-background-color:#263E61; selection-color:#EDF2FA; }
QCheckBox::indicator { background:rgba(28,32,39,120); border-color:#68798F; }
QCheckBox::indicator:checked { background:rgba(0,104,217,120); border-color:#7DB7FF; }
QCheckBox::indicator:disabled { background:rgba(48,56,70,120); border-color:#46546A; }
QPlainTextEdit, QLineEdit, QKeySequenceEdit { background:rgba(21,25,31,120); color:#EDF2FA; placeholder-text-color:#ADB9CC; border-color:#4A5668; selection-background-color:#263E61; selection-color:#EDF2FA; }
QKeySequenceEdit QLineEdit { background:transparent; }
QProgressBar { background:rgba(53,66,86,120); }
QTabBar { background:rgba(17,21,27,120); }
QTabBar::tab { color:#ADB9CC; }
QTabBar::tab:selected { background:rgba(48,59,75,120); color:#EDF2FA; border-color:#556781; }
QTabBar::tab:hover:!selected { background:rgba(38,47,61,120); }
QMenu { background:#202630; color:#EDF2FA; border-color:#526079; }
QMenu::item:selected { background:#263E61; color:#EDF2FA; }
QMenu::item:disabled { color:#8592A5; }
QMenu::separator { background:#455166; }
QToolTip { background:#252D38; color:#EDF2FA; border-color:#63748C; }
QScrollBar:vertical { background:rgba(27,32,40,120); }
QScrollBar::handle:vertical { background:rgba(87,102,125,120); }
QLabel#state[error="true"] { color:#FFABB8; }
"""

DARK_BAR = """
QWidget { color:#EDF2FA; }
QToolButton:hover { background:rgba(59,70,86,120); border-color:#647790; }
QToolButton:pressed { background:rgba(26,36,50,120); }
QToolButton:disabled { color:#8592A5; }
QToolButton#mode { color:#EDF2FA; }
QToolButton#keyboard[active="true"] { background:rgba(38,62,97,120); border-color:#608BC2; }
QToolButton#speak[recording="true"] { background:rgba(75,37,49,120); border-color:#A36176; color:#FFBCC8; }
QToolButton#speak:disabled { background:rgba(38,51,68,120); border-color:#40536D; color:#94A5BD; }
QToolButton#candidate { background:rgba(34,44,59,120); color:#EDF2FA; border-color:#53657D; }
QToolButton#candidate:hover { background:rgba(45,69,102,120); border-color:#80B1F0; }
QLabel#composition { color:#EDF2FA; }
QLabel#status { color:#EDF2FA; }
QLabel#status[error="true"] { color:#FFF0F4; }
QProgressBar { background:rgba(53,66,86,120); }
QMenu { background:#202630; color:#EDF2FA; border-color:#526079; }
QMenu::item:selected { background:#263E61; color:#EDF2FA; }
QMenu::item:disabled { color:#8592A5; }
QMenu::separator { background:#455166; }
QToolTip { background:#252D38; color:#EDF2FA; border-color:#63748C; }
"""

DARK_TOOLS = """
QLineEdit, QListWidget { background:rgba(21,25,31,120); color:#EDF2FA; border-color:#4A5668; selection-background-color:#263E61; selection-color:#EDF2FA; }
QListWidget::item:selected { background:rgba(38,62,97,120); color:#EDF2FA; }
QCheckBox { color:#EDF2FA; }
QCheckBox::indicator { background:rgba(28,32,39,120); border-color:#68798F; }
QCheckBox::indicator:checked { background:rgba(0,104,217,120); border-color:#7DB7FF; }
"""

WORKSPACE_STYLE += '\nQLabel#state[error="true"] { color:#AE2638; }\n'


def style_sheet(surface, theme):
    light, glass = {
        "workspace": (WORKSPACE_STYLE, GLASS_WORKSPACE),
        "bar": (BAR_STYLE, GLASS_BAR),
        "tools": (TOOLS_STYLE, GLASS_TOOLS),
    }[surface]
    return light + glass + ({"workspace": DARK_WORKSPACE, "bar": DARK_BAR, "tools": DARK_TOOLS}[surface] if theme == "dark" else "")


def round_window(widget, radius):
    from PySide6.QtCore import QRectF
    from PySide6.QtGui import QPainterPath, QRegion
    path = QPainterPath()
    path.addRoundedRect(QRectF(widget.rect()), radius, radius)
    widget.setMask(QRegion(path.toFillPolygon().toPolygon()))


def paint_glass(widget, radius, fallback=False, dark=False):
    from PySide6.QtCore import QRectF, Qt
    from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPen
    painter = QPainter(widget)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    bounds = QRectF(widget.rect()).adjusted(.5, .5, -.5, -.5)
    fill = QLinearGradient(0, 0, 0, widget.height())
    tint = (18, 23, 31) if dark else (245, 250, 255)
    minimum_alpha = 210 if fallback else 165 if dark else 140
    for stop, alpha in ((0, 150), (.18, 100), (.48, 82), (.52, 62), (.9, 92), (1, 128)):
        fill.setColorAt(stop, QColor(*tint, max(alpha, minimum_alpha)))
    painter.setBrush(fill)
    painter.setPen(QPen(QColor(255, 255, 255, 100 if dark else 225), 1))
    painter.drawRoundedRect(bounds, radius, radius)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    rim = QLinearGradient(0, 0, 0, widget.height())
    rim.setColorAt(0, QColor(255, 255, 255, 115 if dark else 200))
    rim.setColorAt(1, QColor(150, 176, 205, 65))
    painter.setPen(QPen(rim, 1))
    painter.drawRoundedRect(bounds.adjusted(1, 1, -1, -1), radius - 1, radius - 1)
    painter.end()
