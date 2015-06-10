"""
This file is part of Happypanda.
Happypanda is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 2 of the License, or
any later version.
Happypanda is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
You should have received a copy of the GNU General Public License
along with Happypanda.  If not, see <http://www.gnu.org/licenses/>.
"""

from PyQt5.QtCore import (Qt, QDate, QPoint, pyqtSignal, QThread,
						  QTimer, QObject)
from PyQt5.QtGui import QTextCursor, QIcon
from PyQt5.QtWidgets import (QWidget, QProgressBar, QLabel,
							 QVBoxLayout, QHBoxLayout,
							 QDialog, QGridLayout, QLineEdit,
							 QFormLayout, QPushButton, QTextEdit,
							 QComboBox, QDateEdit, QGroupBox,
							 QDesktopWidget, QMessageBox, QFileDialog,
							 QCompleter, QListWidgetItem,
							 QListWidget, QApplication, QSizePolicy,
							 QCheckBox, QFrame, QListView,
							 QAbstractItemView, QTreeView)
import os, threading, queue, time, logging
from datetime import datetime
from ..utils import tag_to_string, tag_to_dict, title_parser
from ..database import seriesdb, fetch, db
from . import gui_constants

log = logging.getLogger(__name__)
log_i = log.info
log_d = log.debug
log_w = log.warning
log_e = log.error
log_c = log.critical

#class ErrorEvent(QObject):
#	ERROR_MSG = pyqtSignal(str)
#	DONE = pyqtSignal()
#	def __init__(self):
#		super().__init__()

#	def error_event(self):
#		err_q = db.ErrorQueue
#		while True:
#			msg = err_q.get()
#			ERROR_MSG.emit(msg)
#		DONE.emit()

#class ExceptionHandler(QObject):
#	def __init__(self):
#		super().__init__()
#		thread = QThread()

#		def thread_deleteLater():
#			thread.deleteLater

#		err_instance = ErrorEvent()
#		err_instance.moveToThread(thread)
#		err_instance.ERROR_MSG.connect(self.exception_handler)
#		thread.started.connect(err_instance.error_event)
#		err_instance.DONE.connect(thread.deleteLater)
#		thread.start()

#	def exception_handler(self, msg):
#		"Spawns a dialog with the specified msg"
#		db_msg = msg = "The database is not compatible with the current version of the program"
#		msgbox = QMessageBox()
#		if msg == db_msg:
#			msgbox.setText(msg)
#			msgbox.setStandardButtons(QMessageBox.Ok | QMessageBox.Abort)
#			msgbox.setDefaultButton(QMessageBox.Ok)
#			if msgbox.exec() == QMessageBox.Ok:
#				return True
#		else:
#			msgbox.setText(msg)
#			msgbox.setStandardButtons(QMessageBox.Close)
#			msgbox.setDefaultButton(QMessageBox.Close)
#			if msgbox.exec():
#				exit()

#errors = ExceptionHandler()

#def center_parent(parent, child):
#	"centers child window in parent"
#	centerparent = QPoint(
#			parent.x() + (parent.frameGeometry().width() -
#					 child.frameGeometry().width())//2,
#					parent.y() + (parent.frameGeometry().width() -
#					   child.frameGeometry().width())//2)
#	desktop = QApplication.desktop()
#	sg_rect = desktop.screenGeometry(desktop.screenNumber(parent))
#	child_frame = child.frameGeometry()

#	if centerparent.x() < sg_rect.left():
#		centerparent.setX(sg_rect.left())
#	elif (centerparent.x() + child_frame.width()) > sg_rect.right():
#		centerparent.setX(sg_rect.right() - child_frame.width())

#	if centerparent.y() < sg_rect.top():
#		centerparent.setY(sg_rect.top())
#	elif (centerparent.y() + child_frame.height()) > sg_rect.bottom():
#		centerparent.setY(sg_rect.bottom() - child_frame.height())

#	child.move(centerparent)


class SeriesListItem(QListWidgetItem):
	def __init__(self, series=None, parent=None):
		super().__init__(parent)
		self.series = series

class SeriesListView(QWidget):
	SERIES = pyqtSignal(list)
	def __init__(self, parent=None, modal=False):
		super().__init__(parent)
		self.setWindowFlags(Qt.Dialog)

		layout = QVBoxLayout()
		self.setLayout(layout)

		if modal:
			frame = QFrame()
			frame.setFrameShape(frame.StyledPanel)
			modal_layout = QHBoxLayout()
			frame.setLayout(modal_layout)
			layout.addWidget(frame)
			info = QLabel('Select 1 or more series\' to add' +
				 ' to your list.')
			f_folder = QPushButton('Add folders')
			f_folder.clicked.connect(self.from_folder)
			f_files = QPushButton('Add files')
			f_files.clicked.connect(self.from_files)
			modal_layout.addWidget(info, 3, Qt.AlignLeft)
			modal_layout.addWidget(f_folder, 0, Qt.AlignRight)
			modal_layout.addWidget(f_files, 0, Qt.AlignRight)

		check_layout = QHBoxLayout()
		layout.addLayout(check_layout)
		if modal:
			check_layout.addWidget(QLabel('Please uncheck series\' you do' +
							  ' not want to add. (Exisiting series\' won\'t be added'),
							 3)
		else:
			check_layout.addWidget(QLabel('Please uncheck series\' you do' +
							  ' not want to add. (Existing series\' are hidden)'),
							 3)
		self.check_all = QCheckBox('Check/Uncheck All', self)
		self.check_all.setChecked(True)
		self.check_all.stateChanged.connect(self.all_check_state)

		check_layout.addWidget(self.check_all)
		self.view_list = QListWidget()
		self.view_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
		self.view_list.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
		layout.addWidget(self.view_list)
		
		add_btn = QPushButton('Add checked')
		add_btn.clicked.connect(self.return_series)

		cancel_btn = QPushButton('Cancel')
		cancel_btn.clicked.connect(self.close_window)
		btn_layout = QHBoxLayout()

		spacer = QWidget()
		spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
		btn_layout.addWidget(spacer)
		btn_layout.addWidget(add_btn)
		btn_layout.addWidget(cancel_btn)
		layout.addLayout(btn_layout)

		self.resize(500,550)
		frect = self.frameGeometry()
		frect.moveCenter(QDesktopWidget().availableGeometry().center())
		self.move(frect.topLeft())
		self.setWindowTitle('Series List')

	def all_check_state(self, new_state):
		row = 0
		done = False
		while not done:
			item = self.view_list.item(row)
			if item:
				row += 1
				if new_state == Qt.Unchecked:
					item.setCheckState(Qt.Unchecked)
				else:
					item.setCheckState(Qt.Checked)
			else:
				done = True

	def add_series(self, item, name):
		"""
		Constructs an widgetitem to hold the provided item,
		and adds it to the view_list
		"""
		assert isinstance(name, str)
		series_item = SeriesListItem(item)
		series_item.setText(name)
		series_item.setFlags(series_item.flags() | Qt.ItemIsUserCheckable)
		series_item.setCheckState(Qt.Checked)
		self.view_list.addItem(series_item)

	def return_series(self):
		series_list = []
		row = 0
		done = False
		while not done:
			item = self.view_list.item(row)
			if not item:
				done = True
			else:
				if item.checkState() == Qt.Checked:
					series_list.append(item.series)
				row += 1

		self.SERIES.emit(series_list)
		self.close()

	def from_folder(self):
		file_dialog = QFileDialog()
		file_dialog.setFileMode(QFileDialog.DirectoryOnly)
		file_dialog.setOption(QFileDialog.DontUseNativeDialog, True)
		file_view = file_dialog.findChild(QListView, 'listView')
		if file_view:
			file_view.setSelectionMode(QAbstractItemView.MultiSelection)
		f_tree_view = file_dialog.findChild(QTreeView)
		if f_tree_view:
			f_tree_view.setSelectionMode(QAbstractItemView.MultiSelection)

		if file_dialog.exec():
			for path in file_dialog.selectedFiles():
				self.add_series(path, os.path.split(path)[1])


	def from_files(self):
		series_list = QFileDialog.getOpenFileNames(self,
											 'Select 1 or more series to add',
											 filter='Archives (*.zip)')
		for path in series_list[0]:
			#Warning: will break when you add more filters
			if len(path) != 0:
				self.add_series(path, os.path.split(path)[1])

	def close_window(self):
		msgbox = QMessageBox()
		msgbox.setText('Are you sure you want to cancel?')
		msgbox.setStandardButtons(msgbox.Yes | msgbox.No)
		msgbox.setDefaultButton(msgbox.No)
		msgbox.setIcon(msgbox.Question)
		if msgbox.exec() == QMessageBox.Yes:
			self.close()
		

class About(QDialog):
	ON = False #to prevent multiple instances
	def __init__(self):
		super().__init__()
		gpl = """
Happypanda is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 2 of the License, or
any later version.
Happypanda is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
You should have received a copy of the GNU General Public License
along with Happypanda.  If not, see <http://www.gnu.org/licenses/>.
"""
		self.text = QLabel(gpl)
		self.text.setAlignment(Qt.AlignCenter)
		info_lbl = QLabel()
		info_lbl.setText('<a href="https://github.com/Pewpews/happypanda">Visit GitHub Repo</a>')
		info_lbl.setTextFormat(Qt.RichText)
		info_lbl.setTextInteractionFlags(Qt.TextBrowserInteraction)
		info_lbl.setOpenExternalLinks(True)

		layout_ = QVBoxLayout()
		layout_.addWidget(QLabel("<b>Author:</b>\nPewpews\n"))
		layout_.addWidget(self.text, 0, Qt.AlignHCenter)
		layout_.addWidget(info_lbl)
		self.setLayout(layout_)
		self.resize(300,100)
		frect = self.frameGeometry()
		frect.moveCenter(QDesktopWidget().availableGeometry().center())
		self.move(frect.topLeft()-QPoint(0,150))
		self.setAttribute(Qt.WA_DeleteOnClose)
		self.setWindowTitle("About")
		self.setWindowIcon(QIcon(gui_constants.APP_ICO_PATH))
		self.exec()

class Loading(QWidget):
	ON = False #to prevent multiple instances
	def __init__(self, parent=None):
		super().__init__(parent)
		self.widget = QWidget(self)
		self.widget.setStyleSheet("background-color:rgba(0, 0, 0, 0.65)")
		self.progress = QProgressBar()
		self.progress.setStyleSheet("color:white")
		self.text = QLabel()
		self.text.setAlignment(Qt.AlignCenter)
		self.text.setStyleSheet("color:white;background-color:transparent;")
		layout_ = QHBoxLayout()
		inner_layout_ = QVBoxLayout()
		inner_layout_.addWidget(self.text, 0, Qt.AlignHCenter)
		inner_layout_.addWidget(self.progress)
		self.widget.setLayout(inner_layout_)
		layout_.addWidget(self.widget)
		self.setLayout(layout_)
		self.resize(300,100)
		#frect = self.frameGeometry()
		#frect.moveCenter(QDesktopWidget().availableGeometry().center())
		self.move(parent.window().frameGeometry().topLeft() +
			parent.window().rect().center() -
			self.rect().center() - QPoint(self.rect().width()//2,0))
		#self.setAttribute(Qt.WA_DeleteOnClose)
		#self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)

	def mousePressEvent(self, QMouseEvent):
		pass

	def setText(self, string):
		if string != self.text.text():
			self.text.setText(string)

class CompleterTextEdit(QTextEdit):
	"""
	A textedit with autocomplete
	"""
	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self.completer = None
		log_d('Instantiat CompleterTextEdit: OK')

	def setCompleter(self, completer):
		if self.completer:
			self.disconnect(self.completer, 0, self, 0)
		if not completer:
			return None

		completer.setWidget(self)
		completer.setCompletionMode(QCompleter.PopupCompletion)
		completer.setCaseSensitivity(Qt.CaseInsensitive)
		self.completer = completer
		self.completer.insertText.connect(self.insertCompletion)

	def insertCompletion(self, completion):
		tc = self.textCursor()
		extra = (len(completion) -
		   len(self.completer.completionPrefix()))
		tc.movePosition(QTextCursor.Left)
		tc.movePosition(QTextCursor.EndOfWord)
		tc.insertText(completion[-extra:])
		self.setTextCursor(tc)

	def textUnderCursor(self):
		tc = self.textCursor()
		tc.select(QTextCursor.WordUnderCursor)
		return tc.selectedText()

	def focusInEvent(self, event):
		if self.completer:
			self.completer.setWidget(self)
		super().focusInEvent(event)

	def keyPressEvent(self, event):
		if self.completer and self.completer.popup() and \
			self.completer.popup().isVisible():
			if event.key() in (
				Qt.Key_Enter,
				Qt.Key_Return,
				Qt.Key_Tab,
				Qt.Key_Escape,
				Qt.Key_Backtab):
				event.ignore()
				return None

		# to show popup shortcut
		isShortcut = event.modifiers() == Qt.ControlModifier and \
			    event.key() == Qt.Key_Space

		# to complete suggestion inline
		inline = event.key() == Qt.Key_Tab

		if inline:
			self.completer.setCompletionMode(QCompleter.InlineCompletion)
			completionPrefix = self.textUnderCursor()
			if completionPrefix != self.completer.completionPrefix():
				self.completer.setCompletionPrefix(completionPrefix)
			self.completer.complete()

			# set the current suggestion in text box
			self.completer.insertText.emit(self.completer.currentCompletion())
			#reset completion mode
			self.completer.setCompletionMode(QCompleter.PopupCompletion)
			return None
		if not self.completer or not isShortcut:
			super().keyPressEvent(event)
		
		ctrlOrShift = event.modifiers() in (Qt.ControlModifier,
									  Qt.ShiftModifier)
		if ctrlOrShift and event.text() == '':
			return None

		#end of word
		eow = "~!@#$%^&*+{}|:\"<>?,./;'[]\\-="
		
		hasModifier = event.modifiers() != Qt.NoModifier and not ctrlOrShift
		completionPrefix = self.textUnderCursor()

		if not isShortcut:
			if self.completer.popup():
				self.completer.popup().hide()
			return None

		self.completer.setCompletionPrefix(completionPrefix)
		popup = self.completer.popup()
		popup.setCurrentIndex(self.completer.completionModel().index(0,0))
		cr = self.cursorRect()
		cr.setWidth(self.completer.popup().sizeHintForColumn(0) +
			  self.completer.popup().verticalScrollBar().sizeHint().width())
		self.completer.complete(cr)

class CompleterWithData(QCompleter):
	"""
	Instantiate a QCompleter with predefined data
	"""
	insertText = pyqtSignal(str)

	def __init__(self, data, parent=None):
		assert isinstance(data, list)
		super().__init__(data, parent)
		self.activated[str].connect(self.changeCompletion)
		log_d('Instantiate CompleterWithData: OK')

	def changeCompletion(self, completion):
		if completion.find('(') != -1:
			completion = completion[:completion.find('(')]
		print(completion)
		self.insertText.emit(completion)



def return_tag_completer_TextEdit():
	ns = seriesdb.TagDB.get_all_ns()
	for t in seriesdb.TagDB.get_all_tags():
		ns.append(t)
	TextEditCompleter = CompleterTextEdit()
	TextEditCompleter.setCompleter(CompleterWithData(ns))
	return TextEditCompleter

from PyQt5.QtCore import QSortFilterProxyModel
class DatabaseFilterProxyModel(QSortFilterProxyModel):
	"""
	A proxy model to hide items already in database
	Pass a tuple with entries to 'filters' param if you need a custom filter.
	"""
	def __init__(self, filters="", parent=None):
		super().__init__(parent)
		self.filters = tuple(filters)
		self.role = Qt.DisplayRole
		db_data = SeriesDB.get_all_series()
		filter_list = []
		for series in db_data:
			p = os.path.split(series.path)
			filter_list.append(p[1])
		self.filter_list = sorted(filter_list)
		print('Instatiated')

	def set_name_role(self, role):
		self.role = role
		self.invalidateFilter()

	def filterAcceptsRow(self, source_row, index_parent):
		print('Using')
		allow = False
		index = self.sourceModel().index(source_row, 0, index_parent)

		if self.sourceModel() and index.isValid():
			allow = True
			name = index.data(self.role)
			if name.endswith(self.filters):
				if binary_search(name):
					print('Hiding {}'.format(name))
					allow = True
		return allow

# TODO: FIX THIS HORRENDOUS DUPLICATED CODE
class SeriesDialog(QDialog):
	"A window for adding/modifying series"

	series_queue = queue.Queue()
	SERIES = pyqtSignal(list)
	SERIES_EDIT = pyqtSignal(list, int)
	#series_list = [] # might want to extend this to allow mass series adding

	def _init__(self, parent=None):
		super().__init__()
	#TODO: Implement a way to mass add series'
	#IDEA: Extend dialog in a ScrollArea with more forms...

	def initUI(self):
		main_layout = QVBoxLayout()


		f_local = QGroupBox("Folder/ZIP")
		f_local.setCheckable(False)
		main_layout.addWidget(f_local)
		local_layout = QHBoxLayout()
		f_local.setLayout(local_layout)

		choose_folder = QPushButton("From Folder")
		choose_folder.clicked.connect(lambda: self.choose_dir('f'))
		local_layout.addWidget(choose_folder)

		choose_archive = QPushButton("From ZIP")
		choose_archive.clicked.connect(lambda: self.choose_dir('a'))
		local_layout.addWidget(choose_archive)

		self.file_exists_lbl = QLabel()
		local_layout.addWidget(self.file_exists_lbl)
		self.file_exists_lbl.hide()

		f_web = QGroupBox("Metadata from the Web")
		f_web.setCheckable(False)
		main_layout.addWidget(f_web)
		web_main_layout = QVBoxLayout()
		web_layout = QHBoxLayout()
		web_main_layout.addLayout(web_layout)
		ipb_info_l = QHBoxLayout()
		ipb_lbl = QLabel("ipb member id:")
		self.ipb = QLineEdit()
		ipb_pass_lbl = QLabel("ipb pass hash:")
		self.ipb_pass = QLineEdit()
		ipb_btn = QPushButton("Apply")
		ipb_btn.setFixedWidth(70)
		ipb_btn.clicked.connect(self.set_ipb)
		ipb_info_l.addWidget(ipb_lbl)
		ipb_info_l.addWidget(self.ipb)
		ipb_info_l.addWidget(ipb_pass_lbl)
		ipb_info_l.addWidget(self.ipb_pass)
		ipb_info_l.addWidget(ipb_btn)
		web_main_layout.addLayout(ipb_info_l)
		f_web.setLayout(web_main_layout)

		f_series = QGroupBox("Series Info")
		f_series.setCheckable(False)
		main_layout.addWidget(f_series)
		series_layout = QFormLayout()
		f_series.setLayout(series_layout)

		def basic_web(name):
			return QLabel(name), QLineEdit(), QPushButton("Fetch"), QProgressBar()

		url_lbl, url_edit, url_btn, url_prog = basic_web("URL:")
		url_btn.clicked.connect(lambda: self.web_metadata(url_edit.text(), url_btn,
											url_prog))
		url_prog.setTextVisible(False)
		url_prog.setMinimum(0)
		url_prog.setMaximum(0)
		web_layout.addWidget(url_lbl, 0, Qt.AlignLeft)
		web_layout.addWidget(url_edit, 0)
		web_layout.addWidget(url_btn, 0, Qt.AlignRight)
		web_layout.addWidget(url_prog, 0, Qt.AlignRight)
		url_edit.setPlaceholderText("paste g.e-hentai/exhentai gallery link")
		url_prog.hide()


		self.title_edit = QLineEdit()
		self.author_edit = QLineEdit()
		self.descr_edit = QTextEdit()
		self.descr_edit.setFixedHeight(45)
		self.descr_edit.setPlaceholderText("HTML 4 tags are supported")
		self.lang_box = QComboBox()
		self.lang_box.addItems(["English", "Japanese", "Other"])
		self.lang_box.setCurrentIndex(0)
		self.tags_edit = return_tag_completer_TextEdit()
		self.tags_edit.setFixedHeight(70)
		self.tags_edit.setPlaceholderText("Autocomplete enabled. Press Tab (Ctrl + Space to show popup)"+
									"\nnamespace1:tag1, tag2, namespace3:tag3, etc..")
		self.type_box = QComboBox()
		self.type_box.addItems(["Manga", "Doujinshi", "Artist CG Sets", "Game CG Sets",
						  "Western", "Image Sets", "Non-H", "Cosplay", "Other"])
		self.type_box.setCurrentIndex(0)
		#self.type_box.currentIndexChanged[int].connect(self.doujin_show)
		#self.doujin_parent = QLineEdit()
		#self.doujin_parent.setVisible(False)
		self.status_box = QComboBox()
		self.status_box.addItems(["Unknown", "Ongoing", "Completed"])
		self.status_box.setCurrentIndex(0)
		self.pub_edit = QDateEdit()
		self.pub_edit.setCalendarPopup(True)
		self.pub_edit.setDate(QDate.currentDate())
		self.path_lbl = QLabel("unspecified...")
		self.path_lbl.setWordWrap(True)

		self.link_layout = QHBoxLayout()
		self.link_lbl = QLabel("")
		self.link_lbl.setWordWrap(True)
		self.link_edit = QLineEdit()
		self.link_layout.addWidget(self.link_edit)
		self.link_layout.addWidget(self.link_lbl)
		self.link_edit.hide()
		self.link_btn = QPushButton("Modify")
		self.link_btn.setFixedWidth(50)
		self.link_btn2 = QPushButton("Set")
		self.link_btn2.setFixedWidth(40)
		self.link_btn.clicked.connect(self.link_modify)
		self.link_btn2.clicked.connect(self.link_set)
		self.link_layout.addWidget(self.link_btn)
		self.link_layout.addWidget(self.link_btn2)
		self.link_btn2.hide()

		series_layout.addRow("Title:", self.title_edit)
		series_layout.addRow("Author:", self.author_edit)
		series_layout.addRow("Description:", self.descr_edit)
		series_layout.addRow("Language:", self.lang_box)
		series_layout.addRow("Tags:", self.tags_edit)
		series_layout.addRow("Type:", self.type_box)
		series_layout.addRow("Publication Date:", self.pub_edit)
		series_layout.addRow("Path:", self.path_lbl)
		series_layout.addRow("Link:", self.link_layout)

		final_buttons = QHBoxLayout()
		final_buttons.setAlignment(Qt.AlignRight)
		main_layout.addLayout(final_buttons)
		done = QPushButton("Done")
		done.setDefault(True)
		done.clicked.connect(self.accept)
		cancel = QPushButton("Cancel")
		cancel.clicked.connect(self.reject)
		final_buttons.addWidget(cancel)
		final_buttons.addWidget(done)


		self.setLayout(main_layout)
		self.title_edit.setFocus()

	# TODO: complete this... maybe another time.. 
	#def doujin_show(self, index):
	#	if index is 1:
	#		self.doujin_parent.setVisible(True)
	#	else:
	#		self.doujin_parent.setVisible(False)

	def set_ipb(self):
		ipb = self.ipb.text()
		ipb_pass = self.ipb_pass.text()
		from ..settings import s
		s.set_ipb(ipb, ipb_pass)

	def choose_dir(self, mode):
		if mode == 'a':
			name = QFileDialog.getOpenFileName(self, 'Choose archive',
											  filter='*.zip')
			name = name[0]
		else:
			name = QFileDialog.getExistingDirectory(self, 'Choose folder')
		head, tail = os.path.split(name)
		parsed = title_parser(tail)
		self.title_edit.setText(parsed['title'])
		self.author_edit.setText(parsed['artist'])
		self.path_lbl.setText(name)
		l_i = self.lang_box.findText(parsed['language'])
		if l_i != -1:
			self.lang_box.setCurrentIndex(l_i)

		if seriesdb.SeriesDB.check_exists(tail):
			self.file_exists_lbl.setText('<font color="red">Series already exists</font>')
			self.file_exists_lbl.show()
		else: self.file_exists_lbl.hide()

	def check(self):
		if len(self.title_edit.text()) is 0:
			self.title_edit.setFocus()
			self.title_edit.setStyleSheet("border-style:outset;border-width:2px;border-color:red;")
			return False
		elif len(self.author_edit.text()) is 0:
			self.author_edit.setText("Anon")

		if len(self.descr_edit.toPlainText()) is 0:
			self.descr_edit.setText("<i>No description..</i>")

		if self.path_lbl.text() == "unspecified...":
			return False

		return True

	def accept(self):
		from ..database import seriesdb

		def do_chapters(series):
			thread = threading.Thread(target=self.set_chapters, args=(series,), daemon=True)
			thread.start()
			thread.join()
			#return self.series_queue.get()

		if self.check():
			new_series = seriesdb.Series()
			new_series.title = self.title_edit.text()
			new_series.artist = self.author_edit.text()
			new_series.path = self.path_lbl.text()
			new_series.info = self.descr_edit.toPlainText()
			new_series.type = self.type_box.currentText()
			new_series.language = self.lang_box.currentText()
			new_series.status = self.status_box.currentText()
			new_series.tags = tag_to_dict(self.tags_edit.toPlainText())
			qpub_d = self.pub_edit.date().toString("ddMMyyyy")
			dpub_d = datetime.strptime(qpub_d, "%d%m%Y").date()
			new_series.pub_date = dpub_d
			new_series.link = self.link_lbl.text()

			if self.path_lbl.text() == "unspecified...":
				self.SERIES.emit([new_series])
			else:
				updated_series = do_chapters(new_series)
				#for ser in self.series:
				#self.SERIES.emit([updated_series])
			super().accept()

	def set_chapters(self, series_object):
		path = series_object.path
		try:
			con = os.listdir(path) # list all folders in series dir
			chapters = sorted([os.path.join(path,sub) for sub in con if os.path.isdir(os.path.join(path, sub))]) #subfolders
			# if series has chapters divided into sub folders
			if len(chapters) != 0:
				for numb, ch in enumerate(chapters):
					chap_path = os.path.join(path, ch)
					series_object.chapters[numb] = chap_path

			else: #else assume that all images are in series folder
				series_object.chapters[0] = path
				
			#find last edited file
			times = set()
			for root, dirs, files in os.walk(path, topdown=False):
				for img in files:
					fp = os.path.join(root, img)
					times.add(os.path.getmtime(fp))
			series_object.last_update = time.asctime(time.gmtime(max(times)))
		except NotADirectoryError:
			if path[-4:] == '.zip':
				#TODO: add support for folders in archive
				series_object.chapters[0] = path

		#self.series_queue.put(series_object)
		self.SERIES.emit([series_object])
		#seriesdb.SeriesDB.add_series(series_object)
		

	def reject(self):
		if self.check():
			msgbox = QMessageBox()
			msgbox.setText("<font color='red'><b>Noo oniichan! You were about to add a new series.</b></font>")
			msgbox.setInformativeText("Do you really want to discard?")
			msgbox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
			msgbox.setDefaultButton(QMessageBox.No)
			if msgbox.exec() == QMessageBox.Yes:
				super().reject()
		else:
			super().reject()

	def trigger(self, list_of_index=None):
		log_d('Triggered Series Edit/Add Dialog')
		if not list_of_index:
			self.initUI()
		else:
			assert isinstance(list_of_index, list)
			self.position = list_of_index[0].row()
			for index in list_of_index:
				series = index.data(Qt.UserRole+1)
				self.setSeries(series)

		self.resize(500,200)
		frect = self.frameGeometry()
		frect.moveCenter(QDesktopWidget().availableGeometry().center())
		self.move(frect.topLeft()-QPoint(0,180))
		self.setAttribute(Qt.WA_DeleteOnClose)
		self.setWindowTitle("Add a new series")
		self.setWindowIcon(QIcon(gui_constants.APP_ICO_PATH))
		#self.setWindowFlags(Qt.FramelessWindowHint)
		self.exec()

	def web_metadata(self, url, btn_widget, pgr_widget):
		try:
			assert len(url) > 5
		except AssertionError:
			log_w('Invalid URL')
			return None
		self.link_lbl.setText(url)
		f = fetch.Fetch()
		f.web_url = url
		thread = QThread()

		def status(stat):
			def do_hide():
				try:
					pgr_widget.hide()
					btn_widget.show()
				except RuntimeError:
					pass

			if stat:
				do_hide()
			else:
				danger = """QProgressBar::chunk {
					background: QLinearGradient( x1: 0, y1: 0, x2: 1, y2: 0,stop: 0 #FF0350,stop: 0.4999 #FF0020,stop: 0.5 #FF0019,stop: 1 #FF0000 );
					border-bottom-right-radius: 5px;
					border-bottom-left-radius: 5px;
					border: .px solid black;}"""
				pgr_widget.setStyleSheet(danger)
				QTimer.singleShot(3000, do_hide)

		def t_del_later():
			thread.deleteLater
			thread.quit()

		f.moveToThread(thread)
		f.WEB_METADATA.connect(self.set_web_metadata)
		f.WEB_PROGRESS.connect(btn_widget.hide)
		f.WEB_PROGRESS.connect(pgr_widget.show)
		thread.started.connect(f.web)
		f.WEB_STATUS.connect(status)
		f.WEB_STATUS.connect(lambda: f.deleteLater)
		f.WEB_STATUS.connect(lambda: thread.deleteLater)
		thread.start()

	def set_web_metadata(self, metadata):
		assert isinstance(metadata, list)
		for gallery in metadata:
			parsed = title_parser(gallery['title'])
			self.title_edit.setText(parsed['title'])
			self.author_edit.setText(parsed['artist'])
			tags = ""
			lang = ['English', 'Japanese']
			l_i = self.lang_box.findText(parsed['language'])
			if l_i != -1:
				self.lang_box.setCurrentIndex(l_i)
			for n, tag in enumerate(gallery['tags'], 1):
				l_tag = tag.capitalize()
				if l_tag in lang:
					l_index = self.lang_box.findText(l_tag)
					if l_index != -1:
						self.lang_box.setCurrentIndex(l_index)
				else:
					if n == len(gallery['tags']):
						tags += tag
					else:
						tags += tag + ', '
			self.tags_edit.setText(tags)
			pub_dt = datetime.fromtimestamp(int(gallery['posted']))
			pub_string = "{}".format(pub_dt)
			pub_date = QDate.fromString(pub_string.split()[0], "yyyy-MM-dd")
			self.pub_edit.setDate(pub_date)
			t_index = self.type_box.findText(gallery['category'])
			try:
				self.type_box.setCurrentIndex(t_index)
			except:
				self.type_box.setCurrentIndex(0)


	def link_set(self):
		t = self.link_edit.text()
		self.link_edit.hide()
		self.link_lbl.show()
		self.link_lbl.setText(t)
		self.link_btn2.hide()
		self.link_btn.show() 

	def link_modify(self):
		t = self.link_lbl.text()
		self.link_lbl.hide()
		self.link_edit.show()
		self.link_edit.setText(t)
		self.link_btn.hide()
		self.link_btn2.show()

	def setSeries(self, series):
		"To be used for when editing a series"
		self.series = series
		main_layout = QVBoxLayout()

		f_web = QGroupBox("Fetch metadata from Web")
		f_web.setCheckable(False)
		main_layout.addWidget(f_web)
		web_main_layout = QVBoxLayout()
		web_layout = QHBoxLayout()
		web_main_layout.addLayout(web_layout)
		ipb_info_l = QHBoxLayout()
		ipb_lbl = QLabel("ipb member id:")
		self.ipb = QLineEdit()
		ipb_pass_lbl = QLabel("ipb pass hash:")
		self.ipb_pass = QLineEdit()
		ipb_btn = QPushButton("Apply")
		ipb_btn.setFixedWidth(50)
		ipb_btn.clicked.connect(self.set_ipb)
		ipb_info_l.addWidget(ipb_lbl)
		ipb_info_l.addWidget(self.ipb)
		ipb_info_l.addWidget(ipb_pass_lbl)
		ipb_info_l.addWidget(self.ipb_pass)
		ipb_info_l.addWidget(ipb_btn)
		web_main_layout.addLayout(ipb_info_l)
		f_web.setLayout(web_main_layout)

		from ..settings import s
		ipb_dict = s.get_ipb()
		self.ipb.setText(ipb_dict['ipb_id'])
		self.ipb_pass.setText(ipb_dict['ipb_pass'])

		f_series = QGroupBox("Series Info")
		f_series.setCheckable(False)
		main_layout.addWidget(f_series)
		series_layout = QFormLayout()
		f_series.setLayout(series_layout)


		def basic_web(name):
			return QLabel(name), QLineEdit(), QPushButton("Fetch"), QProgressBar()

		url_lbl, url_edit, url_btn, url_prog = basic_web("URL:")
		url_edit.setText(series.link)
		url_btn.clicked.connect(lambda: self.web_metadata(url_edit.text(), url_btn,
													url_prog))
		url_prog.setTextVisible(False)
		url_prog.setMinimum(0)
		url_prog.setMaximum(0)
		web_layout.addWidget(url_lbl, 0, Qt.AlignLeft)
		web_layout.addWidget(url_edit, 0)
		web_layout.addWidget(url_btn, 0, Qt.AlignRight)
		web_layout.addWidget(url_prog, 0, Qt.AlignRight)
		url_edit.setPlaceholderText("paste g.e-hentai/exhentai gallery link")
		url_prog.hide()

		self.title_edit = QLineEdit()
		self.title_edit.setText(series.title)
		self.author_edit = QLineEdit()
		self.author_edit.setText(series.artist)
		self.descr_edit = QTextEdit()
		self.descr_edit.setText(series.info)
		self.descr_edit.setAcceptRichText(True)
		self.descr_edit.setFixedHeight(45)
		self.lang_box = QComboBox()
		self.lang_box.addItems(["English", "Japanese", "Other"])
		if series.language is "English":
			self.lang_box.setCurrentIndex(0)
		elif series.language is "Japanese":
			self.lang_box.setCurrentIndex(1)
		else:
			self.lang_box.setCurrentIndex(2)

		self.tags_edit = return_tag_completer_TextEdit()
		self.tags_edit.setFixedHeight(70)
		self.tags_edit.setPlaceholderText("Autocomplete enabled. Press Tab (Ctrl + Space to show popup)"+
									"\nnamespace1:tag1, tag2, namespace3:tag3, etc..")
		self.tags_edit.setText(tag_to_string(series.tags))

		self.type_box = QComboBox()
		self.type_box.addItems(["Manga", "Doujinshi", "Artist CG Sets", "Game CG Sets",
						  "Western", "Image Sets", "Non-H", "Cosplay", "Other"])

		t_index = self.type_box.findText(series.type)
		try:
			self.type_box.setCurrentIndex(t_index)
		except:
			self.type_box.setCurrentIndex(0)
		#self.type_box.currentIndexChanged[int].connect(self.doujin_show)
		#self.doujin_parent = QLineEdit()
		#self.doujin_parent.setVisible(False)
		self.status_box = QComboBox()
		self.status_box.addItems(["Unknown", "Ongoing", "Completed"])
		if series.status is "Ongoing":
			self.status_box.setCurrentIndex(1)
		elif series.status is "Completed":
			self.status_box.setCurrentIndex(2)
		else:
			self.status_box.setCurrentIndex(0)

		self.pub_edit = QDateEdit()
		self.pub_edit.setCalendarPopup(True)
		series_pub_date = "{}".format(series.pub_date)
		qdate_pub_date = QDate.fromString(series_pub_date, "yyyy-MM-dd")
		self.pub_edit.setDate(qdate_pub_date)
		self.path_lbl = QLabel("unspecified...")
		self.path_lbl.setWordWrap(True)

		self.link_layout = QHBoxLayout()
		self.link_lbl = QLabel("")
		self.link_lbl.setWordWrap(True)
		self.link_edit = QLineEdit()
		self.link_layout.addWidget(self.link_edit)
		self.link_layout.addWidget(self.link_lbl)
		self.link_edit.hide()
		self.link_btn = QPushButton("Modify")
		self.link_btn.setFixedWidth(50)
		self.link_btn2 = QPushButton("Set")
		self.link_btn2.setFixedWidth(40)
		self.link_btn.clicked.connect(self.link_modify)
		self.link_btn2.clicked.connect(self.link_set)
		self.link_layout.addWidget(self.link_btn)
		self.link_layout.addWidget(self.link_btn2)
		self.link_btn2.hide()

		series_layout.addRow("Title:", self.title_edit)
		series_layout.addRow("Author:", self.author_edit)
		series_layout.addRow("Description:", self.descr_edit)
		series_layout.addRow("Language:", self.lang_box)
		series_layout.addRow("Tags:", self.tags_edit)
		series_layout.addRow("Type:", self.type_box)
		series_layout.addRow("Publication Date:", self.pub_edit)
		series_layout.addRow("Path:", self.path_lbl)
		series_layout.addRow("Link:", self.link_layout)

		self.link_lbl.setText(series.link)
		self.path_lbl.setText(series.path)

		final_buttons = QHBoxLayout()
		final_buttons.setAlignment(Qt.AlignRight)
		main_layout.addLayout(final_buttons)
		done = QPushButton("Done")
		done.setDefault(True)
		done.clicked.connect(self.accept_edit)
		cancel = QPushButton("Cancel")
		cancel.clicked.connect(self.reject_edit)
		final_buttons.addWidget(cancel)
		final_buttons.addWidget(done)

		self.setLayout(main_layout)

	def accept_edit(self):

		if self.check():
			new_series = self.series
			new_series.title = self.title_edit.text()
			new_series.artist = self.author_edit.text()
			new_series.path = self.path_lbl.text()
			new_series.info = self.descr_edit.toPlainText()
			new_series.type = self.type_box.currentText()
			new_series.language = self.lang_box.currentText()
			new_series.status = self.status_box.currentText()
			new_series.tags = tag_to_dict(self.tags_edit.toPlainText())
			qpub_d = self.pub_edit.date().toString("ddMMyyyy")
			dpub_d = datetime.strptime(qpub_d, "%d%m%Y").date()
			new_series.pub_date = dpub_d
			new_series.link = self.link_lbl.text()

			#for ser in self.series:
			self.SERIES_EDIT.emit([new_series], self.position)
			super().accept()

	def reject_edit(self):
		super().reject()