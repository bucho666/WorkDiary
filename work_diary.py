import sys
import re
import os
import configparser
from PyQt5 import sip
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

class DiaryEdit(QPlainTextEdit):
  def __init__(self, parent):
    super().__init__(parent)
    self._lineNumber = QWidget(self)
    self._lineNumber.installEventFilter(self)
    self.setCursorWidth(2)
    self.setFont("ＭＳ ゴシック", 9)
    self.setTabStopWidth(self.fontMetrics().width(' ') * 2)
    self.setViewportMargins(self.fontMetrics().width('9') * 4, 0, 0, 0)
    self.setStyleSheet("border: outside; border-left: 1px solid lightGray")

  def eventFilter(self, obj, event):
    if obj == self._lineNumber and event.type() == QEvent.Paint:
      self._paintLineNumber()
      return True
    return False

  def setFont(self, fontName, size):
    font = QFont(fontName, size)
    super().setFont(font)
    self._lineNumber.setFont(font)
    fontWidth = self.fontMetrics().width('W')
    self.setTabStopWidth(fontWidth * 2)
    self.setViewportMargins(fontWidth * 4, 0, 0, 0)

  def keyPressEvent(self, e):
    if e.key() == Qt.Key_Return:
      self._autoIndent(e)
    else:
      super().keyPressEvent(e)
    self.ensureCursorVisible()
    self.update()

  def mousePressEvent(self, e):
    super().mousePressEvent(e)
    self.update()

  def paintEvent(self, e):
    super().paintEvent(e)
    self._paintCurrentLine()
    self._lineNumber.update()

  def resizeEvent(self, e):
    super().resizeEvent(e)
    self._resizeLineNumber()

  def _resizeLineNumber(self):
    lineNumberWidth = self.fontMetrics().width('9') * 4
    self.setViewportMargins(lineNumberWidth, 0, 0, 0)
    r = self.rect()
    self._lineNumber.setGeometry(QRect(r.left(), r.top(), lineNumberWidth, r.height()))

  def _paintLineNumber(self):
    r = self._lineNumber.rect()
    p = QPainter(self._lineNumber)
    p.fillRect(r, Qt.white)
    p.setPen(Qt.gray)
    block = self.firstVisibleBlock()
    lineNumber = block.blockNumber() + 1
    bottom = self.geometry().bottom()
    while block.isValid():
      y = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
      if y >= bottom: break
      p.drawText(0, y, r.width(), r.height(), Qt.AlignRight, str(lineNumber))
      lineNumber += 1
      block = block.next()

  def _paintCurrentLine(self):
    y = self.cursorRect(self.textCursor()).bottom()
    p = QPainter(self.viewport())
    p.setPen(Qt.gray)
    p.drawLine(0, y, self.rect().right(), y)

  def _autoIndent(self, e):
    indent = re.match('^(\s+)', self.textCursor().block().text())
    self.textCursor().insertBlock()
    if indent:
      self.textCursor().insertText(indent.group(0))

class Diary(object):
  def __init__(self, date):
    year = str(date.year())
    month = str(date.month())
    filename = "%s.txt" % date.day()
    self._file_path = os.path.join("data", year, month, filename)

  def save(self, text):
    if not text:
      self._remove()
      return
    os.makedirs(os.path.dirname(self._file_path), exist_ok = True)
    with open(self._file_path, "w") as f:
      f.write(text)

  def load(self):
    if not self.exists():
      return ""
    with open(self._file_path, "r") as f:
      return f.read()

  def _remove(self):
    if self.exists():
      os.remove(self._file_path)

  def exists(self):
    return os.path.exists(self._file_path)

class Config(object):
    _DEFAULT = { 'x': '300', 'y': '300', 'width': '640', 'height': '300' }
    _GEOMETRY= 'geometry'

    def __init__(self, path):
        self._path = path
        self._config = configparser.ConfigParser(self._DEFAULT)
        self._config.add_section(self._GEOMETRY)

    def load(self):
        self._config.read(self._path)
        return self

    def save(self):
        with open(self._path, 'w') as f:
            self._config.write(f)

    def geometry(self):
        return QRect(
            self._config.getint(self._GEOMETRY, 'x'),
            self._config.getint(self._GEOMETRY, 'y'),
            self._config.getint(self._GEOMETRY, 'width'),
            self._config.getint(self._GEOMETRY, 'height'))

    def set_geometry(self, g):
        self._config.set(self._GEOMETRY, 'x', str(g.x()))
        self._config.set(self._GEOMETRY, 'y', str(g.y()))
        self._config.set(self._GEOMETRY, 'width', str(g.width()))
        self._config.set(self._GEOMETRY, 'height', str(g.height()))
        return self

class WorkDiary(QWidget):
  def __init__(self):
    super().__init__()
    self._icon = QIcon("WorkDiary.ico")
    self._config = Config("WorkDiary.ini").load()
    self._initWedgets()
    self._initTrayIcon()
    self._layout()
    self._load_current_diary()
    self._updateCalendar(None, None)
    self.show()

  def closeEvent(self, e):
    self.hide()
    e.ignore()

  def _initWedgets(self):
    self.setWindowIcon(self._icon)
    self.setGeometry(self._config.geometry())
    self.setWindowTitle('WorkDiary')
    self._calendar = QCalendarWidget(self)
    self._calendar.setFixedSize(180, 180)
    self._calendar.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
    self._calendar.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    self._calendar.setGridVisible(True)
    self._calendar.selectionChanged.connect(self._changeDate)
    self._calendar.currentPageChanged.connect(self._updateCalendar)
    self._current_date = self._calendar.selectedDate()
    self._text = DiaryEdit(self)
    self._text.setFocus()

  def _initTrayIcon(self):
    quitAction = QAction('終了', self)
    quitAction.triggered.connect(self.quit)
    trayIconMenu = QMenu(self)
    trayIconMenu.addAction(quitAction)
    self._trayIcon = QSystemTrayIcon(self)
    self._trayIcon.activated.connect(self._trayActivated)
    self._trayIcon.setContextMenu(trayIconMenu)
    self._trayIcon.setIcon(self._icon)
    self._trayIcon.show()

  def quit(self):
    self._trayIcon.hide()
    self._save_current_diary()
    self._config.set_geometry(self.geometry()).save()
    qApp.quit()

  def _trayActivated(self, reason):
    if reason == QSystemTrayIcon.DoubleClick:
      self.setVisible(not self.isVisible())

  def _layout(self):
    hbox, vbox = QHBoxLayout(), QVBoxLayout()
    vbox.addWidget(self._calendar)
    vbox.addLayout(self._make_buttons())
    vbox.addStretch()
    hbox.addLayout(vbox)
    hbox.addWidget(self._text)
    self.setLayout(hbox)

  def _make_buttons(self):
    style = self.style()
    yesterday = QPushButton(style.standardIcon(QStyle.SP_MediaSeekBackward), "")
    yesterday.clicked.connect(lambda e: self._calendar.setSelectedDate(self._calendar.selectedDate().addDays(-1)))
    today = QPushButton(style.standardIcon(QStyle.SP_MediaStop), "")
    today.clicked.connect(lambda e: self._calendar.setSelectedDate(QDate.currentDate()))
    tomorrow =QPushButton(style.standardIcon(QStyle.SP_MediaSeekForward), "") 
    tomorrow.clicked.connect(lambda e: self._calendar.setSelectedDate(self._calendar.selectedDate().addDays(1)))
    layout = QHBoxLayout()
    layout.addWidget(yesterday)
    layout.addWidget(today)
    layout.addWidget(tomorrow)
    return layout

  def _changeDate(self):
    self._save_current_diary()
    self._current_date = self._calendar.selectedDate()
    self._load_current_diary()
    self._updateCalendar(None, None)

  def _save_current_diary(self):
    current_diary = Diary(self._current_date)
    current_diary.save(self._text.toPlainText())

  def _load_current_diary(self):
    self._text.setPlainText(Diary(self._current_date).load())

  def _updateCalendar(self, year, month):
    if not year or not month:
      (year, month) = self._current_date.year(), self._current_date.month()
    today = QDate.currentDate()
    d = QDate(year, month, 1)
    while(d.month() == month):
      f = QTextCharFormat()
      if Diary(d).exists():
        f.setFontWeight(QFont.Bold)
      if d == today:
        f.setBackground(QColor("palegreen"))
      self._calendar.setDateTextFormat(d, f)
      d = d.addDays(1)

if __name__ == '__main__':
  app = QApplication(sys.argv)
  ex = WorkDiary()
  sys.exit(app.exec_())
