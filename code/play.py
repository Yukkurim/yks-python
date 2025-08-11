import sys
import os
import re
import time
import tempfile
import requests
import webbrowser
import importlib.util 
import subprocess
import json 
import shutil 
import zipfile

# --- Check for yt-dlp ---
try:
    import yt_dlp
except ImportError:
    # In a real application, you might prompt the user to install it.
    # For this script, we'll just print an error and exit if it's needed later.
    pass

# QThreadとpyqtSignalを追加
from PyQt6.QtCore import Qt, QUrl, QTimer, QSize, QProcess, QRect, QMargins, QThread, pyqtSignal, QObject
from PyQt6.QtGui import QSyntaxHighlighter, QTextCharFormat, QFont, QTextCursor, QColor, QPainter, QPen, QFontMetrics, QPalette, QBrush, QPixmap
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QListWidgetItem, QFileDialog,
    QSlider, QCheckBox, QLineEdit, QComboBox, QDialog, QMessageBox, QTextEdit, QPlainTextEdit, QColorDialog,
    QMenu, QProgressDialog, QFrame
)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtWebEngineWidgets import QWebEngineView


# Constants/URLs
CURRENT_VERSION = "test build" # Version updated for new features
VERSION_CHECK_URL = "https://yukkurim.github.io/yksplayer-update/version.txt"
UPDATE_DOWNLOAD_URL = "https://yukkurim.github.io/yksplayer-update/update.exe"
FFMPEG_DOWNLOAD_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"


# --- ConfigManager Class ---
class ConfigManager:
    def __init__(self, config_filename="config.json"):
        self.config_filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), config_filename)
        self.config = self._load_config()

    def _load_config(self):
        try:
            if os.path.exists(self.config_filepath):
                with open(self.config_filepath, "r", encoding="utf-8") as f:
                    loaded_config = json.load(f)
                print(f"ConfigManager: Config loaded from {self.config_filepath}: {loaded_config}")
                return loaded_config
            else:
                print(f"ConfigManager: Config file not found at {self.config_filepath}. Starting with empty config.")
                return {}
        except json.JSONDecodeError as e:
            print(f"ConfigManager: Failed to decode config.json at {self.config_filepath}: {e}")
            return {}
        except Exception as e:
            print(f"ConfigManager: Error loading config.json from {self.config_filepath}: {e}")
            return {}

    def _save_config(self):
        try:
            with open(self.config_filepath, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            print(f"ConfigManager: Config saved to {self.config_filepath}: {self.config}")
        except Exception as e:
            print(f"ConfigManager: Error saving config.json to {self.config_filepath}: {e}")

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        self.config[key] = value
        self._save_config()


# --- YouTubeDialog Class (Modified) ---
class YouTubeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("YouTube動画を追加")
        self.setFixedSize(400, 150)

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.urlInput = QLineEdit()
        self.urlInput.setPlaceholderText("YouTubeのURLを入力")
        layout.addWidget(self.urlInput)

        self.playTypeCombo = QComboBox()
        # Add the new download option
        self.playTypeCombo.addItems(["ダウンロードして追加", "埋め込んで再生（非推奨）"])
        layout.addWidget(self.playTypeCombo)

        addBtn = QPushButton("追加")
        layout.addWidget(addBtn)

        addBtn.clicked.connect(self.accept)

    def getData(self):
        return self.urlInput.text().strip(), self.playTypeCombo.currentText()

# --- LicenseDialog Class (No change) ---
class LicenseDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ライセンス")
        self.resize(500, 400)
        layout = QVBoxLayout()
        self.setLayout(layout)

        license_text = """
YKS Player - ライセンス情報

MIT License

Copyright (c) 2025 Yukkurim

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setPlainText(license_text.strip())
        layout.addWidget(text_edit)

        close_btn = QPushButton("閉じる")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)

# --- CustomCSSDialog Class (No change) ---
class CustomCSSDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("カスタムCSS設定")
        self.resize(400, 300)
        self.parent = parent

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.css_edit = QTextEdit()
        self.css_edit.setPlaceholderText("ここにCSSを記述してください。\n例:\nQPushButton { background-color: red; }")
        layout.addWidget(self.css_edit)

        btn_layout = QHBoxLayout()
        apply_btn = QPushButton("適用")
        apply_btn.clicked.connect(self.apply_css)
        btn_layout.addWidget(apply_btn)

        reset_btn = QPushButton("リセット")
        reset_btn.clicked.connect(self.reset_css)
        btn_layout.addWidget(reset_btn)

        close_btn = QPushButton("閉じる")
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

        self.css_edit.setPlainText(self.parent.styleSheet())

    def apply_css(self):
        css = self.css_edit.toPlainText()
        self.parent.setStyleSheet(css)

    def reset_css(self):
        self.css_edit.clear()
        self.parent.setStyleSheet("")

# --- PythonSyntaxHighlighter (No change) ---
class PythonSyntaxHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)

        self.highlightingRules = []

        keywords = [
            'False', 'None', 'True', 'and', 'as', 'assert', 'async',
            'await', 'break', 'class', 'continue', 'def', 'del',
            'elif', 'else', 'except', 'finally', 'for', 'from',
            'global', 'if', 'import', 'in', 'is', 'lambda', 'nonlocal',
            'not', 'or', 'pass', 'raise', 'return', 'try', 'while',
            'with', 'yield'
        ]
        keywordFormat = QTextCharFormat()
        keywordFormat.setForeground(QColor("#569cd6"))
        for word in keywords:
            pattern = r'\b' + word + r'\b'
            self.highlightingRules.append((re.compile(pattern), keywordFormat))

        operators = [
            '=', '==', '!=', '<', '<=', '>', '>=', '\\+', '-', '\\*', '/', '//', '%', '\\*\\*',
            '\\+=', '-=', '\\*=', '/=', '%=', '//=', '\\*\\*=', '&=', '|=', '\\^=', '>>=', '<<=', '&', '|', '^', '~', '<<', '>>'
        ]
        operatorFormat = QTextCharFormat()
        operatorFormat.setForeground(QColor("#d4d4d4"))
        for op in operators:
            self.highlightingRules.append((re.compile(op), operatorFormat))

        builtins = [
            'abs', 'delattr', 'hash', 'memoryview', 'set', 'all', 'dir', 'help', 'min', 'setattr',
            'any', 'divmod', 'hex', 'next', 'slice', 'ascii', 'enumerate', 'id', 'object', 'sorted',
            'bin', 'eval', 'input', 'oct', 'staticmethod', 'bool', 'exec', 'int', 'open', 'str',
            'breakpoint', 'filter', 'isinstance', 'ord', 'sum', 'bytearray', 'float', 'issubclass', 'pow', 'super',
            'bytes', 'format', 'iter', 'list', 'range', 'vars', 'callable', 'frozenset', 'len', 'property', 'type',
            'chr', 'getattr', 'locals', 'repr', 'zip',
            'compile', 'hasattr', 'map', 'reversed', '__import__'
        ]
        builtinFormat = QTextCharFormat()
        builtinFormat.setForeground(QColor("#dcdcaa"))
        for word in builtins:
            pattern = r'\b' + word + r'\b'
            self.highlightingRules.append((re.compile(pattern), builtinFormat))

        self.stringFormat = QTextCharFormat()
        self.stringFormat.setForeground(QColor("#ce9178"))
        self.highlightingRules.append((re.compile(r'".*?"'), self.stringFormat))
        self.highlightingRules.append((re.compile(r"'.*?'"), self.stringFormat))

        self.commentFormat = QTextCharFormat()
        self.commentFormat.setForeground(QColor("#6a9955"))
        self.highlightingRules.append((re.compile(r'#.*'), self.commentFormat))

        self.numberFormat = QTextCharFormat()
        self.numberFormat.setForeground(QColor("#b5cea8"))
        self.highlightingRules.append((re.compile(r'\b[0-9]+\b'), self.numberFormat))
        self.highlightingRules.append((re.compile(r'\b[0-9]*\.[0-9]+\b'), self.numberFormat))

        self.classFormat = QTextCharFormat()
        self.classFormat.setForeground(QColor("#4ec9b0"))
        self.highlightingRules.append((re.compile(r'\bclass\s+([A-Za-z_][A-Za-z0-9_]*)\b'), self.classFormat))

        self.functionFormat = QTextCharFormat()
        self.functionFormat.setForeground(QColor("#dcdcaa"))
        self.highlightingRules.append((re.compile(r'\bdef\s+([A-Za-z_][A-Za-z0-9_]*)\s*\('), self.functionFormat))


    def highlightBlock(self, text):
        for pattern, format in self.highlightingRules:
            for match in pattern.finditer(text):
                self.setFormat(match.start(), match.end() - match.start(), format)

        self.setCurrentBlockState(0)

        startIndex = 0
        if self.previousBlockState() != 1:
            startIndex = text.find('"""')
        while startIndex >= 0:
            endIndex = text.find('"""', startIndex + 3)
            if endIndex == -1:
                self.setCurrentBlockState(1)
                commentLength = len(text) - startIndex
            else:
                commentLength = endIndex - startIndex + 3
            self.setFormat(startIndex, commentLength, self.stringFormat)
            startIndex = text.find('"""', startIndex + commentLength)

        startIndex = 0
        if self.previousBlockState() != 2:
            startIndex = text.find("'''")
        while startIndex >= 0:
            endIndex = text.find("'''", startIndex + 3)
            if endIndex == -1:
                self.setCurrentBlockState(2)
                commentLength = len(text) - startIndex
            else:
                commentLength = endIndex - startIndex + 3
            self.setFormat(startIndex, commentLength, self.stringFormat)
            startIndex = text.find("'''", startIndex + commentLength)

# --- LineNumberArea (No change) ---
class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor
        self.setMouseTracking(True)

    def sizeHint(self):
        return QSize(self.parent().lineNumberAreaWidth(), 0)

    def paintEvent(self, event):
        self.parent().lineNumberAreaPaintEvent(event)

# --- PluginManagerDialog (No change) ---
class PluginManagerDialog(QDialog):
    def __init__(self, parent=None, plugin_handler=None):
        super().__init__(parent)
        self.setWindowTitle("プラグインマネージャー")
        self.resize(500, 400)
        self.plugin_handler = plugin_handler
        self.parent_player = parent

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.plugin_list_widget = QListWidget()
        layout.addWidget(self.plugin_list_widget)

        button_layout = QHBoxLayout()
        self.reload_btn = QPushButton("全て再読み込み")
        self.reload_btn.clicked.connect(self.reload_all_plugins)
        button_layout.addWidget(self.reload_btn)

        self.open_plugins_folder_btn = QPushButton("プラグインフォルダを開く")
        self.open_plugins_folder_btn.clicked.connect(self.open_plugins_folder)
        button_layout.addWidget(self.open_plugins_folder_btn)

        close_btn = QPushButton("閉じる")
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

        self.load_plugin_list()

    def load_plugin_list(self):
        self.plugin_list_widget.clear()
        plugins_dir = self.plugin_handler.get_plugins_dir()
        if not os.path.exists(plugins_dir):
            os.makedirs(plugins_dir)

        for f in os.listdir(plugins_dir):
            if f.endswith(".py") and f != "__init__.py":
                item = QListWidgetItem(f)
                self.plugin_list_widget.addItem(item)

    def reload_all_plugins(self):
        if self.plugin_handler:
            self.plugin_handler.load_all_plugins()
            self.load_plugin_list()
            QMessageBox.information(self, "完了", "全てのプラグインを再読み込みしました。")
        else:
            QMessageBox.warning(self, "エラー", "プラグインハンドラーが見つかりません。")

    def open_plugins_folder(self):
        plugins_dir = self.plugin_handler.get_plugins_dir()
        if sys.platform == "win32":
            os.startfile(plugins_dir)
        elif sys.platform == "darwin":
            subprocess.call(["open", plugins_dir])
        else:
            subprocess.call(["xdg-open", plugins_dir])

# --- PluginEditorDialog (No change) ---
class PluginEditorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("プラグインエディター")
        self.resize(800, 600)
        self.parent = parent

        self.current_plugin_path = None

        layout = QVBoxLayout()
        self.setLayout(layout)

        file_toolbar_layout = QHBoxLayout()
        self.plugin_combo = QComboBox()
        self.plugin_combo.setMinimumWidth(200)
        file_toolbar_layout.addWidget(self.plugin_combo)
        self.plugin_combo.currentIndexChanged.connect(self.load_selected_plugin)


        self.load_btn = QPushButton("開く")
        self.load_btn.clicked.connect(self.load_plugin_file)
        file_toolbar_layout.addWidget(self.load_btn)

        self.save_btn = QPushButton("保存")
        self.save_btn.clicked.connect(self.save_plugin_file)
        file_toolbar_layout.addWidget(self.save_btn)

        file_toolbar_layout.addStretch()
        layout.addLayout(file_toolbar_layout)

        self.code_editor = QPlainTextEdit()
        font = QFont("Consolas" if os.name == "nt" else "Monospace")
        font.setPointSize(10)
        self.code_editor.setFont(font)
        self.code_editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.code_editor.setTabStopDistance(QFontMetrics(font).horizontalAdvance(' ') * 4)
        self.code_editor.setStyleSheet("""
            QPlainTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #444;
                padding-left: 5px;
            }
            QPlainTextEdit::hover {
                border: 1px solid #555;
            }
            LineNumberArea {
                background: #252526;
                color: #858585;
                border-right: 1px solid #333;
            }
        """)
        layout.addWidget(self.code_editor)

        self.highlighter = PythonSyntaxHighlighter(self.code_editor.document())

        self.line_number_area = LineNumberArea(self.code_editor)
        self.code_editor.blockCountChanged.connect(self.update_line_number_area_width)
        self.code_editor.updateRequest.connect(self.update_line_number_area)
        self.code_editor.cursorPositionChanged.connect(self.highlight_current_line)
        self.update_line_number_area_width(0)

        editor_layout = QHBoxLayout()
        editor_layout.addWidget(self.line_number_area)
        editor_layout.addWidget(self.code_editor)
        layout.addLayout(editor_layout)

        bottom_buttons_layout = QHBoxLayout()
        self.reload_all_plugins_btn = QPushButton("プラグインを全て再読み込み")
        self.reload_all_plugins_btn.clicked.connect(self.reload_all_plugins)
        bottom_buttons_layout.addWidget(self.reload_all_plugins_btn)

        close_btn = QPushButton("閉じる")
        close_btn.clicked.connect(self.close)
        bottom_buttons_layout.addWidget(close_btn)
        layout.addLayout(bottom_buttons_layout)

        self.load_plugin_list()
        self.highlight_current_line()

    def get_plugins_dir(self):
        plugins_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plugins")
        os.makedirs(plugins_dir, exist_ok=True)
        return plugins_dir

    def load_plugin_list(self):
        self.plugin_combo.clear()
        self.plugin_combo.addItem("新しいプラグイン...")

        plugins_dir = self.get_plugins_dir()
        plugin_files = sorted([f for f in os.listdir(plugins_dir) if f.endswith(".py") and f != "__init__.py"])
        for f in plugin_files:
            self.plugin_combo.addItem(f)

        if plugin_files:
            self.plugin_combo.setCurrentIndex(1)
        else:
            self.new_plugin()

    def load_selected_plugin(self, index):
        if index == 0:
            self.new_plugin()
            return

        plugin_filename = self.plugin_combo.currentText()
        self.current_plugin_path = os.path.join(self.get_plugins_dir(), plugin_filename)
        try:
            with open(self.current_plugin_path, "r", encoding="utf-8") as f:
                self.code_editor.setPlainText(f.read())
            self.setWindowTitle(f"プラグインエディター - {plugin_filename}")
        except Exception as e:
            QMessageBox.warning(self, "エラー", f"プラグインファイルの読み込みに失敗しました:\n{e}")
            self.new_plugin()

    def new_plugin(self):
        self.code_editor.clear()
        self.current_plugin_path = None
        self.setWindowTitle("プラグインエディター - 新しいプラグイン")
        template_code = """
# YKS Player プラグインテンプレート

# この関数は、YKS Playerが起動した際、またはプラグインが再読み込みされた際に一度だけ呼び出されます。
# player_instance: YKSPlayerクラスのインスタンス
# ここでUI要素を追加したり、YKSPlayerのイベントに接続したりできます。
def setup(player_instance):
    player_instance.log_message("Example Plugin: setup() が呼び出されました！")

    # 例1: 再生/一時停止ボタンがクリックされたときにメッセージを表示する
    # これは直接ボタンのシグナルに接続する例です。
    # player_instance.play_pause_btn.clicked.connect(lambda: on_play_pause_clicked(player_instance))

    # 例2: プレイリストのアイテムがダブルクリックされたときに何かをする
    # player_instance.playlist_widget.itemDoubleClicked.connect(
    #     lambda item: on_playlist_double_clicked(player_instance, item)
    # )

# 以下にプラグインのカスタムロジックを記述します。

# def on_play_pause_clicked(player_instance):
#     QMessageBox.information(
#         player_instance,
#         "プラグインからの通知",
#         "再生/一時停止ボタンが押されました！"
#     )
#     player_instance.log_message("プラグイン: 再生/一時停止ボタンが押されました。", "info")

# def on_playlist_double_clicked(player_instance, item):
#     player_instance.log_message(f"プラグイン: プレイリストアイテムがダブルクリックされました: {item.text()}", "info")
#     # 例: ダブルクリックされたアイテムのURLを取得して表示
#     idx = player_instance.playlist_widget.row(item)
#     if 0 <= idx < len(player_instance.media_list):
#         media_item = player_instance.media_list[idx]
#         QMessageBox.information(
#             player_instance,
#             "プラグインからの情報",
#             f"選択されたファイルのパス: {media_item.url}"
#         )


# プラグインのアンロード時に呼び出される（プラグインが再読み込みされる際などに使用）
# ここで、setupで設定したイベント接続を解除するなど、リソースを解放します。
def teardown(player_instance):
    player_instance.log_message("Example Plugin: teardown() が呼び出されました。")
    # 例: イベント接続を解除
    # try:
    #     player_instance.play_pause_btn.clicked.disconnect(lambda: on_play_pause_clicked(player_instance))
    # except TypeError: # 既に切断されている場合など
    #     pass
"""
        self.code_editor.setPlainText(template_code.strip())
        self.plugin_combo.setCurrentIndex(0)

    def load_plugin_file(self):
        plugins_dir = self.get_plugins_dir()
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "プラグインファイルを開く",
            plugins_dir,
            "Pythonファイル (*.py);;すべてのファイル (*)"
        )
        if filepath:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    self.code_editor.setPlainText(f.read())
                self.current_plugin_path = filepath
                self.setWindowTitle(f"プラグインエディター - {os.path.basename(filepath)}")
                self.load_plugin_list()
                index = self.plugin_combo.findText(os.path.basename(filepath))
                if index != -1:
                    self.plugin_combo.setCurrentIndex(index)
            except Exception as e:
                QMessageBox.warning(self, "エラー", f"ファイルの読み込みに失敗しました:\n{e}")

    def save_plugin_file(self):
        if self.current_plugin_path is None or not os.path.exists(self.current_plugin_path):
            plugins_dir = self.get_plugins_dir()
            filepath, _ = QFileDialog.getSaveFileName(
                self,
                "プラグインファイルを保存",
                os.path.join(plugins_dir, "new_plugin.py"),
                "Pythonファイル (*.py);;すべてのファイル (*)"
            )
        else:
            filepath = self.current_plugin_path

        if filepath:
            if not filepath.endswith(".py"):
                filepath += ".py"

            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(self.code_editor.toPlainText())
                self.current_plugin_path = filepath
                self.setWindowTitle(f"プラグインエディター - {os.path.basename(filepath)}")
                QMessageBox.information(self, "保存完了", f"'{os.path.basename(filepath)}' を保存しました。")
                self.load_plugin_list()
                index = self.plugin_combo.findText(os.path.basename(filepath))
                if index != -1:
                    self.plugin_combo.setCurrentIndex(index)
            except Exception as e:
                QMessageBox.warning(self, "エラー", f"ファイルの保存に失敗しました:\n{e}")

    def reload_all_plugins(self):
        if self.parent and hasattr(self.parent, 'plugin_handler'):
            self.parent.plugin_handler.load_all_plugins()
            QMessageBox.information(self, "プラグイン再読み込み", "全てのプラグインを再読み込みしました。")
        else:
            QMessageBox.warning(self, "エラー", "YKSPlayerインスタンスにアクセスできません。")

    def update_line_number_area_width(self, newBlockCount):
        self.code_editor.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)

    def lineNumberAreaWidth(self):
        digits = 1
        max_value = max(1, self.code_editor.blockCount())
        while max_value >= 10:
            max_value /= 10
            digits += 1
        space = 3 + self.code_editor.fontMetrics().horizontalAdvance('9') * digits
        return space

    def update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())

        if rect.contains(self.code_editor.viewport().rect()):
            self.update_line_number_area_width(0)

    def lineNumberAreaPaintEvent(self, event):
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor("#252526"))

        block = self.code_editor.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = int(self.code_editor.blockBoundingGeometry(block).translated(self.code_editor.contentOffset()).top())
        bottom = top + int(self.code_editor.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(blockNumber + 1)
                painter.setPen(QPen(QColor("#858585")))
                painter.drawText(0, top, self.line_number_area.width() - 3, self.code_editor.fontMetrics().height(),
                                 Qt.AlignmentFlag.AlignRight, number)

            block = block.next()
            top = bottom
            bottom = top + int(self.code_editor.blockBoundingRect(block).height())
            blockNumber += 1
        painter.end()

    def highlight_current_line(self):
        extraSelections = []
        if not self.code_editor.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            lineColor = QColor("#333333")
            selection.format.setBackground(lineColor)
            selection.format.setProperty(QTextCharFormat.Property.FullWidthSelection, True)
            selection.cursor = self.code_editor.textCursor()
            selection.cursor.clearSelection()
            extraSelections.append(selection)
        self.code_editor.setExtraSelections(extraSelections)


# --- MediaItem Class (Modified for serialization) ---
class MediaItem:
    def __init__(self, name, url, type_):
        self.name = name
        self.url = url
        self.type = type_  # "local_video", "local_audio", "youtube_video"

    def to_dict(self):
        return {
            "name": self.name,
            "url": self.url,
            "type": self.type
        }

    @classmethod
    def from_dict(cls, data):
        return cls(data["name"], data["url"], data["type"])

# --- PluginHandler (No change) ---
class PluginHandler:
    def __init__(self, player_instance):
        self.player_instance = player_instance
        self.loaded_plugins = {}

    def get_plugins_dir(self):
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "plugins")

    def load_plugin(self, plugin_name):
        plugin_path = os.path.join(self.get_plugins_dir(), f"{plugin_name}.py")
        if not os.path.exists(plugin_path):
            print(f"PluginHandler: プラグイン '{plugin_name}.py' が見つかりません。")
            return None

        if plugin_name in self.loaded_plugins:
            self.unload_plugin(plugin_name)

        try:
            unique_module_name = f"{plugin_name}_{int(time.time() * 1000)}"
            spec = importlib.util.spec_from_file_location(unique_module_name, plugin_path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[unique_module_name] = module
            spec.loader.exec_module(module)

            if hasattr(module, 'setup'):
                module.setup(self.player_instance)
                print(f"PluginHandler: プラグイン '{plugin_name}' をロードし、setup() を実行しました。")
                self.player_instance.log_message(f"プラグイン '{plugin_name}' をロードしました。", "info")
            else:
                print(f"PluginHandler: プラグイン '{plugin_name}' に setup() 関数がありません。")
                self.player_instance.log_message(f"プラグイン '{plugin_name}': setup() 関数がありません。", "warning")

            self.loaded_plugins[plugin_name] = module
            return module
        except Exception as e:
            print(f"PluginHandler: プラグイン '{plugin_name}' のロード中にエラーが発生しました: {e}")
            self.player_instance.log_message(f"プラグイン '{plugin_name}' のロードに失敗しました: {e}", "error")
            return None

    def unload_plugin(self, plugin_name):
        if plugin_name in self.loaded_plugins:
            module = self.loaded_plugins[plugin_name]
            if hasattr(module, 'teardown'):
                try:
                    module.teardown(self.player_instance)
                    print(f"PluginHandler: プラグイン '{plugin_name}' の teardown() を実行しました。")
                except Exception as e:
                    print(f"PluginHandler: プラグイン '{plugin_name}' の teardown() 実行中にエラー: {e}")
                    self.player_instance.log_message(f"プラグイン '{plugin_name}': teardown() 実行中にエラー: {e}", "warning")

            for mod_name, mod_obj in list(sys.modules.items()):
                if mod_obj is module:
                    del sys.modules[mod_name]
                    break
            
            del self.loaded_plugins[plugin_name]
            print(f"PluginHandler: プラグイン '{plugin_name}' をアンロードしました。")
            self.player_instance.log_message(f"プラグイン '{plugin_name}' をアンロードしました。", "info")

    def load_all_plugins(self):
        for name in list(self.loaded_plugins.keys()):
            self.unload_plugin(name)

        plugins_dir = self.get_plugins_dir()
        os.makedirs(plugins_dir, exist_ok=True)

        found_plugins = 0
        for filename in os.listdir(plugins_dir):
            if filename.endswith(".py") and filename != "__init__.py":
                plugin_name = os.path.splitext(filename)[0]
                self.load_plugin(plugin_name)
                found_plugins += 1
        if found_plugins == 0:
            print("PluginHandler: ロードするプラグインが見つかりませんでした。")
            self.player_instance.log_message("ロードするプラグインが見つかりませんでした。", "info")

# --- ThemeDialog Class (New) ---
class ThemeDialog(QDialog):
    def __init__(self, parent=None, config_manager=None):
        super().__init__(parent)
        self.setWindowTitle("テーマ設定")
        self.setFixedSize(300, 200)
        self.config_manager = config_manager
        self.parent_player = parent

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.theme_combo = QComboBox()
        self.theme_combo.addItem("ダークモード", "dark")
        self.theme_combo.addItem("ライトモード", "light")
        self.theme_combo.addItem("システムに従う", "system")
        
        # Load current theme from config
        current_theme = self.config_manager.get("theme", "dark")
        index = self.theme_combo.findData(current_theme)
        if index != -1:
            self.theme_combo.setCurrentIndex(index)
        
        layout.addWidget(QLabel("テーマを選択:"))
        layout.addWidget(self.theme_combo)

        apply_btn = QPushButton("適用")
        apply_btn.clicked.connect(self.apply_theme)
        layout.addWidget(apply_btn)

        close_btn = QPushButton("閉じる")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)

    def apply_theme(self):
        selected_theme = self.theme_combo.currentData()
        self.config_manager.set("theme", selected_theme)
        self.parent_player.apply_theme_from_config() # Notify main player to apply theme
        QMessageBox.information(self, "テーマ適用", "テーマが適用されました。")

# --- SettingsDialog Class (Modified for Theme and Background Image settings) ---
class SettingsDialog(QDialog):
    def __init__(self, parent=None, current_version=None, config_manager=None):
        super().__init__(parent)
        self.setWindowTitle("設定")
        self.setFixedSize(320, 480)
        self.parent = parent
        self.config_manager = config_manager

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.version_label = QLabel(f"現在のバージョン: {current_version}")
        layout.addWidget(self.version_label)

        self.check_update_btn = QPushButton("オンラインアップデート")
        layout.addWidget(self.check_update_btn)
        self.check_update_btn.clicked.connect(self.on_check_update)

        self.discord_btn = QPushButton("開発Discord鯖")
        layout.addWidget(self.discord_btn)
        self.discord_btn.clicked.connect(lambda: webbrowser.open("https://discord.gg/myDFmyK69R"))

        self.github_btn = QPushButton("Githubリポジトリ")
        layout.addWidget(self.github_btn)
        self.github_btn.clicked.connect(lambda: webbrowser.open("https://github.com/Yukkurim/yks-python"))

        self.discord_btn = QPushButton("WEBツール版")
        layout.addWidget(self.discord_btn)
        self.discord_btn.clicked.connect(lambda: webbrowser.open("https://yukkurim.github.io/yks"))

        self.license_btn = QPushButton("ライセンス")
        layout.addWidget(self.license_btn)
        self.license_btn.clicked.connect(self.open_license)

        self.custom_css_btn = QPushButton("カスタムCSS")
        layout.addWidget(self.custom_css_btn)
        self.custom_css_btn.clicked.connect(self.open_custom_css)
        
        # New Theme Button
        self.theme_btn = QPushButton("テーマ設定")
        layout.addWidget(self.theme_btn)
        self.theme_btn.clicked.connect(self.open_theme_settings)



        self.plugin_manager_btn = QPushButton("プラグインマネージャー")
        layout.addWidget(self.plugin_manager_btn)
        self.plugin_manager_btn.clicked.connect(self.open_plugin_manager)

        self.plugin_editor_btn = QPushButton("プラグインエディター")
        layout.addWidget(self.plugin_editor_btn)
        self.plugin_editor_btn.clicked.connect(self.open_plugin_editor)

        layout.addStretch()

        close_btn = QPushButton("閉じる")
        layout.addWidget(close_btn)
        close_btn.clicked.connect(self.close)

    def on_check_update(self):
        self.check_update_btn.setEnabled(False)
        self.version_label.setText("アップデート確認中...")
        QApplication.processEvents()

        self.parent.check_update(manual=True)

        self.version_label.setText(f"現在のバージョン: {CURRENT_VERSION}")
        self.check_update_btn.setEnabled(True)

    def open_license(self):
        dlg = LicenseDialog(self)
        dlg.exec()

    def open_custom_css(self):
        dlg = CustomCSSDialog(self.parent)
        dlg.exec()

    def open_plugin_manager(self):
        dlg = PluginManagerDialog(self, self.parent.plugin_handler)
        dlg.exec()

    def open_plugin_editor(self):
        dlg = PluginEditorDialog(self)
        dlg.exec()

    # New method to open theme settings
    def open_theme_settings(self):
        dlg = ThemeDialog(self, self.config_manager)
        dlg.exec()

# --- Weather Worker (New) ---
class WeatherWorker(QObject):
    """
    バックグラウンドで気象情報を取得するためのワーカースレッド
    """
    weather_updated = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    finished = pyqtSignal()  

    def run(self):
        try:
            # 1. IPアドレスから緯度経度を取得 (キー不要のAPI)
            geo_response = requests.get("http://ip-api.com/json", timeout=10)
            geo_response.raise_for_status()
            geo_data = geo_response.json()

            if geo_data.get("status") != "success":
                self.error_occurred.emit("位置情報の取得に失敗")
                return

            lat = geo_data["lat"]
            lon = geo_data["lon"]
            city = geo_data.get("city", "不明な都市")

            # 2. 緯度経度から天気を取得 (キー不要のOpen-Meteo API)
            weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
            weather_response = requests.get(weather_url, timeout=10)
            weather_response.raise_for_status()
            weather_data = weather_response.json()
            
            temperature = weather_data["current_weather"]["temperature"]
            weather_text = f"{city}: {temperature}°C"
            self.weather_updated.emit(weather_text)

        except requests.exceptions.RequestException as e:
            self.error_occurred.emit("ネットワークエラー")
            print(f"WeatherWorker Error: {e}")
        except Exception as e:
            self.error_occurred.emit("取得エラー")
            print(f"WeatherWorker Error: {e}")
        finally:
            self.finished.emit() 


# --- YKSPlayer Class (Modified for new features) ---
class YKSPlayer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("▶ YKS player for Client")
        self.resize(900, 600)

        self.config_manager = ConfigManager()
        
        # --- Paths for downloads and FFmpeg ---
        app_dir = os.path.dirname(os.path.abspath(__file__))
        self.downloads_path = os.path.join(app_dir, "downloads")
        os.makedirs(self.downloads_path, exist_ok=True)
        self.ffmpeg_path = os.path.join(app_dir, "ffmpeg.exe")
        self.last_downloaded_file = None

        # self.log_widget の初期化をここで行う
        self.log_widget = QTextEdit()
        self.log_widget.setReadOnly(True)
        self.log_widget.setMaximumHeight(80)
        self.log_widget.setStyleSheet("background-color: #2b2b2b; color: #f0f0f0; border: 1px solid #444;")
        
        # log_widget が初期化された後にログメッセージを送信
        self.log_message(f"YKSPlayer: Config initialized. Current config: {self.config_manager.config}", "info")

        self.plugin_handler = PluginHandler(self)

        self.media_list = []
        self.current_index = -1
        self.is_repeat = False
        self.is_muted = False # Track mute state

        self.build_ui() # build_ui の中で self.log_widget をレイアウトに追加

        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)

        self.video_widget = QVideoWidget()
        self.video_widget.setMinimumSize(640, 360)
        self.media_container_layout.addWidget(self.video_widget)

        self.youtube_view = QWebEngineView()
        self.youtube_view.setVisible(False)
        self.media_container_layout.addWidget(self.youtube_view)

        self.player.setVideoOutput(self.video_widget)

        self.player.positionChanged.connect(self.on_position_changed)
        self.player.durationChanged.connect(self.on_duration_changed)
        self.player.mediaStatusChanged.connect(self.on_media_status_changed)
        self.player.errorOccurred.connect(self.on_error)

        # メインのUI更新タイマー
        self.ui_update_timer = QTimer(self)
        self.ui_update_timer.setInterval(1000) # 1秒ごとに更新
        self.ui_update_timer.timeout.connect(self.update_ui_elements)
        self.ui_update_timer.start()
        
        # 初期時刻表示
        self.update_time_label()

        # 天気情報取得のセットアップ
        self.setup_weather_system()

        self.check_update(manual=False)
        self.plugin_handler.load_all_plugins()

        self.load_queue_state()
        self.apply_theme_from_config() # Apply theme on startup

        self.log_message("YKS Player 起動完了。", "info")

    def build_ui(self):
        self.main_layout = QHBoxLayout()
        self.setLayout(self.main_layout)

        # --- 左側のコンテナ (情報パネル + プレイリスト) ---
        left_container_widget = QWidget()
        left_container_layout = QVBoxLayout()
        left_container_layout.setContentsMargins(0,0,0,0)
        left_container_widget.setLayout(left_container_layout)
        left_container_widget.setMaximumWidth(400)
        self.main_layout.addWidget(left_container_widget)

        # --- 時刻と天気を表示する情報パネル ---
        self.info_panel = QFrame()
        self.info_panel.setFrameShape(QFrame.Shape.StyledPanel)
        self.info_panel.setFrameShadow(QFrame.Shadow.Raised)
        self.info_panel.setStyleSheet("QFrame { border: 1px solid #444; border-radius: 4px; }")
        info_panel_layout = QVBoxLayout()
        self.info_panel.setLayout(info_panel_layout)

        self.time_label = QLabel("時刻: --:--:--")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_label.setStyleSheet("font-size: 16px; font-weight: bold; border: none;")
        info_panel_layout.addWidget(self.time_label)

        self.weather_label = QLabel("天気: 読込中...")
        self.weather_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.weather_label.setStyleSheet("font-size: 14px; border: none;")
        info_panel_layout.addWidget(self.weather_label)
        
        left_container_layout.addWidget(self.info_panel)


        # --- プレイリストウィジェット ---
        self.playlist_widget = QListWidget()
        left_container_layout.addWidget(self.playlist_widget)
        self.playlist_widget.itemClicked.connect(self.on_playlist_click)
        self.playlist_widget.setAcceptDrops(True)
        self.playlist_widget.setDragDropMode(QListWidget.DragDropMode.DropOnly)
        self.playlist_widget.dragEnterEvent = self.playlist_drag_enter_event
        self.playlist_widget.dropEvent = self.playlist_drop_event
        self.playlist_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.playlist_widget.customContextMenuRequested.connect(self.show_playlist_context_menu)


        self.right_layout = QVBoxLayout()
        self.main_layout.addLayout(self.right_layout)

        self.header_layout = QHBoxLayout()
        self.right_layout.addLayout(self.header_layout)

        title_label = QLabel("▶ YKS player")
        title_label.setStyleSheet("font-weight:bold; font-size: 20px; color: white;")
        self.header_layout.addWidget(title_label)

        self.add_file_btn = QPushButton("動画/音声を追加")
        self.add_file_btn.clicked.connect(self.add_files)
        self.header_layout.addWidget(self.add_file_btn)

        self.add_youtube_btn = QPushButton("YouTube動画を追加")
        self.add_youtube_btn.clicked.connect(self.add_youtube)
        self.header_layout.addWidget(self.add_youtube_btn)

        self.settings_btn = QPushButton("設定")
        self.settings_btn.clicked.connect(self.open_settings)
        self.header_layout.addWidget(self.settings_btn)
        
        self.generate_share_btn = QPushButton("共有ファイルを生成")
        self.generate_share_btn.clicked.connect(self.generate_share_file)
        self.header_layout.addWidget(self.generate_share_btn)

        self.load_share_btn = QPushButton("共有ファイルをロード")
        self.load_share_btn.clicked.connect(self.load_share_file)
        self.header_layout.addWidget(self.load_share_btn)

        self.header_layout.addStretch()

        self.media_container = QWidget()
        self.media_container_layout = QVBoxLayout()
        self.media_container.setLayout(self.media_container_layout)
        self.media_container.setStyleSheet("background-color: black; border-radius: 8px;")
        self.right_layout.addWidget(self.media_container)

        self.audio_icon = QLabel("♪ Music")
        self.audio_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.audio_icon.setStyleSheet("color: #888; font-size: 72px;")
        self.audio_icon.setVisible(False)
        self.media_container_layout.addWidget(self.audio_icon)

        info_layout = QVBoxLayout()
        self.right_layout.addLayout(info_layout)
        self.song_title_label = QLabel("タイトル: -")
        self.song_title_label.setStyleSheet("color: white; font-weight: bold; font-size: 16px;")
        self.artist_label = QLabel("アーティスト: -")
        self.artist_label.setStyleSheet("color: #ccc; font-size: 14px;")
        info_layout.addWidget(self.song_title_label)
        info_layout.addWidget(self.artist_label)

        self.seek_slider = QSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setRange(0, 1000)
        self.seek_slider.sliderMoved.connect(self.seek)
        self.right_layout.addWidget(self.seek_slider)

        time_layout = QHBoxLayout()
        self.right_layout.addLayout(time_layout)
        self.current_time_label = QLabel("00:00")
        self.current_time_label.setStyleSheet("color: #aaa;")
        self.duration_label = QLabel("00:00")
        self.duration_label.setStyleSheet("color: #aaa;")
        time_layout.addWidget(self.current_time_label)
        time_layout.addStretch()
        time_layout.addWidget(self.duration_label)

        controls_layout = QHBoxLayout()
        self.right_layout.addLayout(controls_layout)

        self.prev_btn = QPushButton("⏮ 前へ")
        self.prev_btn.clicked.connect(self.prev_track)
        controls_layout.addWidget(self.prev_btn)

        self.play_pause_btn = QPushButton("▶ 再生")
        self.play_pause_btn.clicked.connect(self.play_pause)
        controls_layout.addWidget(self.play_pause_btn)

        self.next_btn = QPushButton("⏭ 次へ")
        self.next_btn.clicked.connect(self.next_track)
        controls_layout.addWidget(self.next_btn)

        self.repeat_btn = QPushButton("リピートOFF")
        self.repeat_btn.clicked.connect(self.toggle_repeat)
        controls_layout.addWidget(self.repeat_btn)

        self.mute_btn = QPushButton("ミュートOFF")
        self.mute_btn.clicked.connect(self.toggle_mute)
        controls_layout.addWidget(self.mute_btn)

        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(100)
        self.volume_slider.valueChanged.connect(self.change_volume)
        controls_layout.addWidget(self.volume_slider)

        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["0.5x", "1x", "1.25x", "1.5x", "2x"])
        self.speed_combo.setCurrentIndex(1)
        self.speed_combo.currentIndexChanged.connect(self.change_speed)
        controls_layout.addWidget(self.speed_combo)

        self.right_layout.addWidget(self.log_widget)

        self.update_mute_button_style()
        self.update_repeat_button_style()

    # --- New: Time and Weather Update Logic ---
    def setup_weather_system(self):
        """天気情報取得のためのスレッドとタイマーを初期化する"""
        self.weather_thread = QThread()
        self.weather_worker = WeatherWorker()
        self.weather_worker.moveToThread(self.weather_thread)

        self.weather_thread.started.connect(self.weather_worker.run)
        self.weather_worker.weather_updated.connect(self.update_weather_label)
        self.weather_worker.error_occurred.connect(self.update_weather_error)
        self.weather_worker.finished.connect(self.weather_thread.quit)
        self.weather_worker.finished.connect(self.weather_worker.deleteLater)
        self.weather_thread.finished.connect(self.weather_thread.deleteLater)

        # 30分ごとに天気を更新するタイマー
        self.weather_update_timer = QTimer(self)
        self.weather_update_timer.setInterval(30 * 60 * 1000) # 30分
        self.weather_update_timer.timeout.connect(self.request_weather_update)
        self.weather_update_timer.start()

        # 起動時に一度だけ天気を取得
        self.request_weather_update()
        
    def request_weather_update(self):
        """天気情報の更新をリクエストする"""
        if not self.weather_thread.isRunning():
            self.weather_label.setText("天気: 更新中...")
            self.weather_thread.start()

    def update_weather_label(self, weather_text):
        """天気ラベルを更新するスロット"""
        self.weather_label.setText(f"天気: {weather_text}")

    def update_weather_error(self, error_message):
        """天気取得エラー時にラベルを更新するスロット"""
        self.weather_label.setText(f"天気: {error_message}")
        
    def update_time_label(self):
        """時刻ラベルを更新する"""
        current_time = time.strftime("%H:%M:%S")
        self.time_label.setText(f"時刻: {current_time}")

    def update_ui_elements(self):
        """UI要素を定期的に更新する"""
        self.update_time_label()
        # シークバーの更新は再生中のみ行う
        if self.player.isPlaying():
            pos = self.player.position()
            self.on_position_changed(pos)

    # --- Online Update related (No change) ---
    def check_update(self, manual=False):
        """
        起動時または手動で呼ぶ
        manual=Trueならユーザー操作なのでメッセージ出す
        """
        try:
            response = requests.get(VERSION_CHECK_URL, timeout=5)
            if response.status_code == 200:
                latest_version = response.text.strip()
                if self.is_newer_version(latest_version, CURRENT_VERSION):
                    msg = f"新しいバージョン {latest_version} が利用可能です。ダウンロードしますか？"
                    if manual:
                        reply = QMessageBox.question(self, "アップデート確認", msg,
                                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                        if reply == QMessageBox.StandardButton.Yes:
                            self.download_update()
                    else:
                        QMessageBox.information(self, "アップデート情報", msg)
                else:
                    if manual:
                        QMessageBox.information(self, "アップデート情報", "最新バージョンです。")
            else:
                if manual:
                    QMessageBox.warning(self, "アップデート情報", "バージョン情報の取得に失敗しました。")
        except Exception as e:
            if manual:
                QMessageBox.warning(self, "アップデート情報", f"アップデート確認中にエラーが発生しました:\n{e}")

    def is_newer_version(self, latest, current):
        def ver_to_tuple(v): return tuple(map(int, v.split(".")))
        try:
            return ver_to_tuple(latest) > ver_to_tuple(current)
        except:
            return False

    def download_update(self):
        try:
            tmp_file = tempfile.gettempdir() + "/yksplayer_update.exe"
            r = requests.get(UPDATE_DOWNLOAD_URL, stream=True)
            with open(tmp_file, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            QMessageBox.information(self, "ダウンロード完了", "更新プログラムを実行します。アプリは終了します。")
            QProcess.startDetached(tmp_file)
            self.close()
        except Exception as e:
            QMessageBox.warning(self, "エラー", f"更新のダウンロードに失敗しました:\n{e}")

    # --- Settings Dialog (Modified to pass config_manager) ---
    def open_settings(self):
        dlg = SettingsDialog(self, current_version=CURRENT_VERSION, config_manager=self.config_manager)
        dlg.exec()

    # --- Existing Media and UI Operation Methods (Modified for queue persistence and webhook) ---
    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "動画/音声ファイルを選択",
            "",
            "動画ファイル (*.mp4 *.avi *.mkv *.mov);;音声ファイル (*.mp3 *.wav *.aac *.flac);;すべてのファイル (*)"
        )
        if not files:
            return
        self.add_files_to_queue(files)
        
    def add_files_to_queue(self, files):
        initial_media_count = len(self.media_list)
        for f in files:
            name = os.path.basename(f)
            ext = os.path.splitext(f)[1].lower()
            if ext in [".mp3", ".wav", ".aac", ".flac"]:
                type_ = "local_audio"
            elif ext in [".mp4", ".avi", ".mkv", ".mov"]:
                type_ = "local_video"
            else:
                self.log_message(f"サポートされていないファイル形式をスキップしました: {f}", "warning")
                continue
            self.media_list.append(MediaItem(name, f, type_))
        self.build_playlist()
        if initial_media_count == 0 and self.media_list: # If playlist was empty, load the first added item
            self.load_media(0)
        self.save_queue_state()

    def add_youtube(self):
        dlg = YouTubeDialog(self)
        if not dlg.exec():
            return

        url, play_type = dlg.getData()
        if not url:
            return

        m = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})", url)
        if not m:
            QMessageBox.warning(self, "エラー", "無効なYouTube URLです")
            return

        if play_type == "埋め込んで再生（非推奨）":
            video_id = m.group(1)
            embed_url = f"https://www.youtube.com/embed/{video_id}?autoplay=1"
            name = f"[YouTube] {video_id}"
            self.media_list.append(MediaItem(name, embed_url, "youtube_video"))
            self.build_playlist()
            if self.current_index == -1:
                self.load_media(len(self.media_list) - 1) # Load the newly added item
            self.save_queue_state()
        
        elif play_type == "ダウンロードして追加":
            self.download_youtube_video(url)

    def build_playlist(self):
        self.playlist_widget.clear()
        for i, item in enumerate(self.media_list):
            lw_item = QListWidgetItem(item.name)
            if i == self.current_index:
                lw_item.setBackground(QColor(Qt.GlobalColor.darkGray))
                lw_item.setForeground(QColor(Qt.GlobalColor.white))
            self.playlist_widget.addItem(lw_item)

    def load_media(self, index: int):
        if index < 0 or index >= len(self.media_list):
            self.player.stop()
            self.song_title_label.setText("タイトル: -")
            self.artist_label.setText("アーティスト: -")
            self.current_time_label.setText("00:00")
            self.duration_label.setText("00:00")
            self.save_queue_state()
            return

        self.current_index = index
        item = self.media_list[index]

        self.audio_icon.setVisible(False)
        self.youtube_view.setVisible(False)
        self.video_widget.setVisible(False)
        self.player.stop()

        if item.type == "youtube_video":
            self.youtube_view.setVisible(True)
            self.youtube_view.load(QUrl(item.url))
            self.seek_slider.setEnabled(False)
            self.play_pause_btn.setEnabled(False)
            self.repeat_btn.setEnabled(False)
            self.mute_btn.setEnabled(False) 
            self.volume_slider.setEnabled(False)
            self.speed_combo.setEnabled(False)
            self.song_title_label.setText(f"タイトル: {item.name}")
            self.artist_label.setText("アーティスト: YouTube")
            self.current_time_label.setText("--:--")
            self.duration_label.setText("--:--")
        else:
            self.video_widget.setVisible(True)
            url = QUrl.fromLocalFile(item.url)
            self.player.setSource(url)
            self.player.play()
            self.play_pause_btn.setText("⏸ 一時停止")
            self.seek_slider.setEnabled(True)
            self.play_pause_btn.setEnabled(True)
            self.repeat_btn.setEnabled(True)
            self.mute_btn.setEnabled(True)
            self.volume_slider.setEnabled(True)
            self.speed_combo.setEnabled(True)

            if item.type == "local_audio":
                self.audio_icon.setVisible(True)
                self.song_title_label.setText(f"タイトル: {item.name}")
                self.artist_label.setText("アーティスト: -")
            else:
                self.audio_icon.setVisible(False)
                self.song_title_label.setText(f"タイトル: {item.name}")
                self.artist_label.setText("アーティスト: -")
        
        self.build_playlist()
        self.save_queue_state()

    def on_playlist_click(self, item: QListWidgetItem):
        idx = self.playlist_widget.row(item)
        self.load_media(idx)

    def on_position_changed(self, pos):
        if not self.seek_slider.isSliderDown():
            self.seek_slider.setValue(int(pos))
        self.current_time_label.setText(self.format_time(pos / 1000))

    def on_duration_changed(self, dur):
        self.seek_slider.setRange(0, int(dur))
        self.duration_label.setText(self.format_time(dur / 1000))

    def seek(self, pos):
        self.player.setPosition(pos)

    def on_media_status_changed(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            if self.is_repeat:
                self.player.setPosition(0)
                self.player.play()
            else:
                if self.current_index < len(self.media_list) - 1:
                    self.load_media(self.current_index + 1)
                else:
                    if self.media_list:
                         self.load_media(0)
                    else:
                        self.player.stop()
                        self.song_title_label.setText("タイトル: -")
                        self.artist_label.setText("アーティスト: -")
                        self.current_time_label.setText("00:00")
                        self.duration_label.setText("00:00")
            self.save_queue_state()

    def on_error(self):
        error_string = self.player.errorString()
        print(f"Playback Error: {error_string}")
        QMessageBox.critical(self, "再生エラー", f"メディアの再生中にエラーが発生しました:\n{error_string}")
        self.log_message(f"再生エラー: {error_string}", "error")

    def play_pause(self):
        if self.player.isPlaying():
            self.player.pause()
            self.play_pause_btn.setText("▶ 再生")
        else:
            self.player.play()
            self.play_pause_btn.setText("⏸ 一時停止")

    def prev_track(self):
        if self.current_index > 0:
            self.load_media(self.current_index - 1)
        elif self.media_list:
            self.load_media(len(self.media_list) - 1)

    def next_track(self):
        if self.current_index < len(self.media_list) - 1:
            self.load_media(self.current_index + 1)
        elif self.media_list:
            self.load_media(0)

    def toggle_repeat(self):
        self.is_repeat = not self.is_repeat
        self.update_repeat_button_style()

    def update_repeat_button_style(self):
        if self.is_repeat:
            self.repeat_btn.setText("リピートON")
            self.repeat_btn.setStyleSheet("background-color: #569cd6; color: white;")
        else:
            self.repeat_btn.setText("リピートOFF")
            self.repeat_btn.setStyleSheet("")

    def toggle_mute(self):
        self.is_muted = not self.is_muted
        self.audio_output.setMuted(self.is_muted)
        self.update_mute_button_style()

    def update_mute_button_style(self):
        if self.is_muted:
            self.mute_btn.setText("ミュートON")
            self.mute_btn.setStyleSheet("background-color: #d65656; color: white;")
        else:
            self.mute_btn.setText("ミュートOFF")
            self.mute_btn.setStyleSheet("")

    def change_volume(self, value):
        self.audio_output.setVolume(value / 100)

    def change_speed(self, index):
        speeds = [0.5, 1.0, 1.25, 1.5, 2.0]
        if 0 <= index < len(speeds):
            self.player.setPlaybackRate(speeds[index])

    def apply_theme_from_config(self):
        theme = self.config_manager.get("theme", "dark")
        stylesheet = ""
        if theme == "dark":
            stylesheet = self.get_dark_theme_stylesheet()
        elif theme == "light":
            stylesheet = self.get_light_theme_stylesheet()
        elif theme == "system":
            QApplication.instance().setStyleSheet("")

        QApplication.instance().setStyleSheet(stylesheet)
        
        # テーマ固有のスタイルを再適用
        if theme == "dark":
            self.info_panel.setStyleSheet("QFrame { border: 1px solid #444; border-radius: 4px; background-color: #2b2b2b; } QLabel { border: none; }")
        elif theme == "light":
             self.info_panel.setStyleSheet("QFrame { border: 1px solid #ccc; border-radius: 4px; background-color: #e8e8e8; } QLabel { border: none; }")
        else: # System
             self.info_panel.setStyleSheet("QFrame { border: 1px solid gray; border-radius: 4px; } QLabel { border: none; }")
        
        self.update_mute_button_style()
        self.update_repeat_button_style()

    def get_dark_theme_stylesheet(self):
        return """
        QWidget { background-color: #121212; color: #e0e0e0; }
        QPushButton { background-color: #1e1e1e; border: 1px solid #444; border-radius: 4px; padding: 4px; }
        QPushButton:hover { background-color: #333; }
        QListWidget { background-color: #1e1e1e; border: 1px solid #444; }
        QListWidget::item { padding: 5px; }
        QListWidget::item:selected { background-color: #444; color: white; }

        QSlider::groove:horizontal { height: 6px; background: #444; border-radius: 3px; }
        QSlider::handle:horizontal { background: #888; border-radius: 8px; width: 16px; margin: -5px 0; }
        QComboBox { background-color: #1e1e1e; border: 1px solid #444; padding: 2px; border-radius: 4px; }
        QLineEdit { background-color: #1e1e1e; border: 1px solid #444; padding: 4px; border-radius: 4px; }
        QCheckBox { spacing: 8px; }

        QTextEdit { background-color: #1e1e1e; color: #e0e0e0; border: 1px solid #444; border-radius: 4px; padding: 5px; }
        QDialog { background-color: #1e1e1e; color: #e0e0e0; }
        QLabel { color: #e0e0e0; }
        QFrame { border: 1px solid #444; border-radius: 4px; }
        """

    def get_light_theme_stylesheet(self):
        return """
        QWidget { background-color: #f0f0f0; color: #333333; }
        QPushButton { background-color: #e0e0e0; border: 1px solid #ccc; border-radius: 4px; padding: 4px; }
        QPushButton:hover { background-color: #d0d0d0; }
        QListWidget { background-color: #ffffff; border: 1px solid #ccc; }
        QListWidget::item { padding: 5px; }
        QListWidget::item:selected { background-color: #aaddff; color: #333333; }

        QSlider::groove:horizontal { height: 6px; background: #cccccc; border-radius: 3px; }
        QSlider::handle:horizontal { background: #999999; border-radius: 8px; width: 16px; margin: -5px 0; }
        QComboBox { background-color: #ffffff; border: 1px solid #cccccc; padding: 2px; border-radius: 4px; }
        QLineEdit { background-color: #ffffff; border: 1px solid #cccccc; padding: 4px; border-radius: 4px; }
        QCheckBox { spacing: 8px; }

        QTextEdit { background-color: #ffffff; color: #333333; border: 1px solid #cccccc; border-radius: 4px; padding: 5px; }
        QDialog { background-color: #f0f0f0; color: #333333; }
        QLabel { color: #333333; }
        QFrame { border: 1px solid #ccc; border-radius: 4px; }
        """

    def check_and_download_ffmpeg(self):
        if os.path.exists(self.ffmpeg_path):
            return True

        reply = QMessageBox.question(self, "FFmpegが必要です",
                                     "動画をダウンロードするにはFFmpegが必要です。\n"
                                     "自動的にダウンロードしますか？ (約 60-80 MB)",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.No:
            return False

        temp_dir = tempfile.gettempdir()
        temp_zip_path = os.path.join(temp_dir, "ffmpeg-essentials.zip")
        temp_extract_path = os.path.join(temp_dir, "ffmpeg-extracted")

        progress = QProgressDialog("FFmpegをダウンロード中...", "キャンセル", 0, 100, self)
        progress.setWindowTitle("FFmpeg ダウンロード")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.show()

        try:
            self.log_message(f"FFmpegをダウンロードしています: {FFMPEG_DOWNLOAD_URL}", "info")
            response = requests.get(FFMPEG_DOWNLOAD_URL, stream=True, timeout=15)
            response.raise_for_status()
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0

            with open(temp_zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if progress.wasCanceled():
                        self.log_message("FFmpegのダウンロードがキャンセルされました。", "warning")
                        return False
                    f.write(chunk)
                    downloaded_size += len(chunk)
                    if total_size > 0:
                        percentage = (downloaded_size / total_size) * 100
                        progress.setValue(int(percentage))
                    QApplication.processEvents()
            
            progress.setLabelText("FFmpegを展開中...")
            progress.setValue(100)
            QApplication.processEvents()

            self.log_message("FFmpegを展開しています...", "info")
            if os.path.exists(temp_extract_path):
                shutil.rmtree(temp_extract_path)
            with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_extract_path)

            progress.setLabelText("ffmpeg.exeを探しています...")
            QApplication.processEvents()

            found_ffmpeg = False
            for root, _, files in os.walk(temp_extract_path):
                if "ffmpeg.exe" in files:
                    source_ffmpeg = os.path.join(root, "ffmpeg.exe")
                    self.log_message(f"ffmpeg.exeが見つかりました: {source_ffmpeg}", "info")
                    shutil.move(source_ffmpeg, self.ffmpeg_path)
                    found_ffmpeg = True
                    break
            
            progress.close()

            if found_ffmpeg:
                QMessageBox.information(self, "成功", "FFmpegが正常にインストールされました。")
                self.log_message("FFmpegが正常にインストールされました。", "info")
                return True
            else:
                QMessageBox.critical(self, "エラー", "ダウンロードしたアーカイブにffmpeg.exeが見つかりませんでした。")
                self.log_message("ダウンロードしたアーカイブにffmpeg.exeが見つかりませんでした。", "error")
                return False

        except Exception as e:
            progress.close()
            QMessageBox.critical(self, "ダウンロード失敗", f"FFmpegのダウンロードまたはインストールに失敗しました:\n{e}")
            self.log_message(f"FFmpegのダウンロードまたはインストールに失敗しました: {e}", "error")
            return False
        finally:
            if os.path.exists(temp_zip_path):
                os.remove(temp_zip_path)
            if os.path.exists(temp_extract_path):
                shutil.rmtree(temp_extract_path)

    def download_youtube_video(self, url):
        try:
            import yt_dlp
        except ImportError:
            QMessageBox.critical(self, "エラー", "yt-dlpライブラリが見つかりません。\n'pip install yt-dlp' を実行してインストールしてください。")
            self.log_message("yt-dlp is not installed.", "error")
            return

        if not self.check_and_download_ffmpeg():
            self.log_message("ダウンロードにはFFmpegが必要ですが、インストールされませんでした。", "error")
            return

        progress_dialog = QProgressDialog("ダウンロード準備中...", "キャンセル", 0, 100, self)
        progress_dialog.setWindowTitle("YouTube動画をダウンロード中")
        progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        progress_dialog.setAutoClose(False) 
        progress_dialog.setAutoReset(False)
        progress_dialog.show()

        def progress_hook(d):
            if progress_dialog.wasCanceled():
                raise yt_dlp.utils.DownloadCancelled("Download cancelled by user.")

            if d['status'] == 'downloading':
                total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
                downloaded_bytes = d.get('downloaded_bytes')
                if total_bytes and downloaded_bytes:
                    percentage = (downloaded_bytes / total_bytes) * 100
                    progress_dialog.setValue(int(percentage))
                    progress_dialog.setLabelText(f"ダウンロード中: {d['_percent_str']} / {d['_total_bytes_str']} @ {d['_speed_str']}")
            
            elif d['status'] == 'finished':
                progress_dialog.setValue(100)
                progress_dialog.setLabelText("ダウンロード完了、ファイルを処理中...")
                self.last_downloaded_file = d.get('info_dict', {}).get('_filename')
            
            QApplication.processEvents()

        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': os.path.join(self.downloads_path, '%(title)s [%(id)s].%(ext)s'),
            'progress_hooks': [progress_hook],
            'ffmpeg_location': self.ffmpeg_path,
            'nocheckcertificate': True,
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            }],
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                self.log_message(f"ダウンロードを開始します: {url}", "info")
                ydl.download([url])
            
            progress_dialog.close()

            if self.last_downloaded_file and os.path.exists(self.last_downloaded_file):
                self.log_message(f"ダウンロード成功: {os.path.basename(self.last_downloaded_file)}", "info")
                self.add_files_to_queue([self.last_downloaded_file])
            else:
                self.log_message("ダウンロードは完了しましたが、出力ファイルが見つかりませんでした。", "error")
                QMessageBox.warning(self, "ダウンロードエラー", "ダウンロードは完了しましたが、ファイルが見つかりませんでした。")

        except yt_dlp.utils.DownloadCancelled:
            progress_dialog.close()
            self.log_message("YouTubeのダウンロードがキャンセルされました。", "warning")
        except Exception as e:
            progress_dialog.close()
            self.log_message(f"yt-dlpダウンロードエラー: {e}", "error")
            QMessageBox.critical(self, "ダウンロードエラー", f"ダウンロード中にエラーが発生しました:\n{e}")

    def save_queue_state(self):
        queue_filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "queue_state.json")
        try:
            data = {
                "media_list": [item.to_dict() for item in self.media_list],
                "current_index": self.current_index
            }
            with open(queue_filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            self.log_message("キューの状態を保存しました。", "info")
        except Exception as e:
            self.log_message(f"キューの状態の保存に失敗しました: {e}", "error")

    def load_queue_state(self):
        queue_filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "queue_state.json")
        if os.path.exists(queue_filepath):
            try:
                with open(queue_filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                loaded_media_list = [MediaItem.from_dict(d) for d in data.get("media_list", [])]
                loaded_current_index = data.get("current_index", -1)

                valid_media_list = []
                original_indices = {id(item): i for i, item in enumerate(loaded_media_list)}
                current_item_id = id(loaded_media_list[loaded_current_index]) if 0 <= loaded_current_index < len(loaded_media_list) else None

                for item in loaded_media_list:
                    if item.type.startswith("local_") and not os.path.exists(item.url):
                        self.log_message(f"ファイルが見つかりません: {item.url} (キューから削除)", "warning")
                    else:
                        valid_media_list.append(item)
                
                self.media_list = valid_media_list
                self.current_index = -1
                if current_item_id:
                    for i, item in enumerate(self.media_list):
                        if id(item) == current_item_id:
                            self.current_index = i
                            break

                self.build_playlist()
                if self.media_list and self.current_index != -1:
                    self.load_media(self.current_index)
                elif self.media_list:
                    self.load_media(0)
                
                self.log_message("キューの状態をロードしました。", "info")
            except Exception as e:
                self.log_message(f"キューの状態のロードに失敗しました: {e}", "error")
                self.media_list = []
                self.current_index = -1
        else:
            self.log_message("保存されたキューの状態は見つかりませんでした。", "info")

    def generate_share_file(self):
        if not self.media_list:
            QMessageBox.warning(self, "共有ファイルを生成", "プレイリストが空です。")
            return

        default_filename = f"yks_share_{time.strftime('%Y%m%d_%H%M%S')}.zip"
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "共有ファイルを保存",
            default_filename,
            "YKS Player共有ファイル (*.zip);;すべてのファイル (*)"
        )
        if not filepath:
            return

        if not filepath.endswith(".zip"):
            filepath += ".zip"

        temp_dir = os.path.join(tempfile.gettempdir(), f"yks_share_temp_{os.getpid()}")
        os.makedirs(temp_dir, exist_ok=True)

        try:
            share_media_list = []
            copied_files = {}
            for i, item in enumerate(self.media_list):
                item_dict = item.to_dict()
                if item.type.startswith("local_"):
                    original_path = item.url
                    if os.path.exists(original_path):
                        relative_path = os.path.basename(original_path)
                        destination_path = os.path.join(temp_dir, relative_path)
                        
                        if original_path not in copied_files:
                            shutil.copy2(original_path, destination_path)
                            copied_files[original_path] = relative_path
                        
                        item_dict["url"] = relative_path
                    else:
                        self.log_message(f"共有ファイル生成: ローカルファイルが見つかりません: {original_path}", "warning")
                        continue
                share_media_list.append(item_dict)

            share_data = {
                "media_list": share_media_list,
                "current_index": self.current_index
            }
            playlist_json_path = os.path.join(temp_dir, "playlist.json")
            with open(playlist_json_path, "w", encoding="utf-8") as f:
                json.dump(share_data, f, indent=4, ensure_ascii=False)

            shutil.make_archive(os.path.splitext(filepath)[0], 'zip', temp_dir)
            QMessageBox.information(self, "共有ファイルを生成", f"共有ファイル '{os.path.basename(filepath)}' を生成しました。")
            self.log_message(f"共有ファイル '{os.path.basename(filepath)}' を生成しました。", "info")

        except Exception as e:
            QMessageBox.critical(self, "エラー", f"共有ファイルの生成に失敗しました:\n{e}")
            self.log_message(f"共有ファイルの生成に失敗しました: {e}", "error")
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

    def load_share_file(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "共有ファイルをロード",
            "",
            "YKS Player共有ファイル (*.zip);;すべてのファイル (*)"
        )
        if not filepath:
            return

        temp_extract_dir = os.path.join(tempfile.gettempdir(), f"yks_load_share_temp_{os.getpid()}")
        os.makedirs(temp_extract_dir, exist_ok=True)

        try:
            shutil.unpack_archive(filepath, temp_extract_dir, 'zip')

            playlist_json_path = os.path.join(temp_extract_dir, "playlist.json")
            if not os.path.exists(playlist_json_path):
                QMessageBox.warning(self, "共有ファイルをロード", "選択されたファイルに 'playlist.json' が見つかりません。")
                return

            with open(playlist_json_path, "r", encoding="utf-8") as f:
                share_data = json.load(f)
            
            loaded_media_list = []
            for item_dict in share_data.get("media_list", []):
                item_type = item_dict.get("type")
                item_url = item_dict.get("url")
                if item_type.startswith("local_"):
                    local_path = os.path.join(temp_extract_dir, item_url)
                    if os.path.exists(local_path):
                        loaded_media_list.append(MediaItem(item_dict["name"], local_path, item_type))
                    else:
                        self.log_message(f"ロード失敗: 共有ファイル内のローカルファイルが見つかりません: {item_url}", "warning")
                else:
                    loaded_media_list.append(MediaItem.from_dict(item_dict))

            if not loaded_media_list:
                QMessageBox.warning(self, "共有ファイルをロード", "共有ファイルから有効なメディアをロードできませんでした。")
                return

            self.media_list = loaded_media_list
            self.current_index = share_data.get("current_index", -1)
            
            self.build_playlist()
            if self.media_list and self.current_index != -1:
                self.load_media(self.current_index)
            elif self.media_list:
                self.load_media(0)

            QMessageBox.information(self, "共有ファイルをロード", "共有ファイルを正常にロードしました。")
            self.log_message("共有ファイルをロードしました。", "info")

        except Exception as e:
            QMessageBox.critical(self, "エラー", f"共有ファイルのロードに失敗しました:\n{e}")
            self.log_message(f"共有ファイルのロードに失敗しました: {e}", "error")
        finally:
            if os.path.exists(temp_extract_dir):
                shutil.rmtree(temp_extract_dir)

    def show_playlist_context_menu(self, position):
        item = self.playlist_widget.itemAt(position)
        if item:
            menu = QMenu(self)
            delete_action = menu.addAction("キューから削除")
            action = menu.exec(self.playlist_widget.mapToGlobal(position))
            if action == delete_action:
                self.remove_selected_from_queue()

    def remove_selected_from_queue(self):
        selected_items = self.playlist_widget.selectedItems()
        if not selected_items:
            return

        indices_to_remove = sorted([self.playlist_widget.row(item) for item in selected_items], reverse=True)

        for idx in indices_to_remove:
            if idx == self.current_index:
                self.player.stop()
                self.song_title_label.setText("タイトル: -")
                self.artist_label.setText("アーティスト: -")
                self.current_time_label.setText("00:00")
                self.duration_label.setText("00:00")
                self.current_index = -1

            del self.media_list[idx]
            self.playlist_widget.takeItem(idx)

            if idx < self.current_index:
                self.current_index -= 1
            
        if self.current_index >= len(self.media_list):
            self.current_index = -1
        
        if self.player.mediaStatus() == QMediaPlayer.MediaStatus.NoMedia and self.media_list:
            if self.current_index == -1:
                self.load_media(0)
            elif self.current_index < len(self.media_list):
                self.load_media(self.current_index)
            else: 
                 self.load_media(len(self.media_list) - 1)
        
        self.build_playlist()
        self.save_queue_state()
        self.log_message(f"{len(indices_to_remove)} 個のアイテムをキューから削除しました。", "info")

    def playlist_drag_enter_event(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def playlist_drop_event(self, event):
        if event.mimeData().hasUrls():
            files_to_add = []
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    files_to_add.append(url.toLocalFile())
            if files_to_add:
                self.add_files_to_queue(files_to_add)
            event.acceptProposedAction()
        else:
            event.ignore()

    def closeEvent(self, event):
        self.save_queue_state()
        self.weather_thread.quit()
        self.weather_thread.wait()
        super().closeEvent(event)

    def log_message(self, message: str, level="info"):
        color = "#e0e0e0"
        if level == "warning":
            color = "#ffd700"
        elif level == "error":
            color = "#ff6347"

        formatted_message = f'<span style="color: {color};">[{time.strftime("%H:%M:%S")}] {message}</span><br>'
        self.log_widget.insertHtml(formatted_message)
        self.log_widget.verticalScrollBar().setValue(self.log_widget.verticalScrollBar().maximum())

    @staticmethod
    def format_time(seconds):
        m, s = divmod(int(seconds), 60)
        return f"{m:02d}:{s:02d}"


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    player = YKSPlayer()
    player.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()