#!/usr/bin/env python2
# vim:fileencoding=utf-8

from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__ = 'GPL v3'
__copyright__ = '2018, Thiago Oliveira'
__docformat__ = 'restructuredtext en'

# PyQt libraries
from PyQt5.Qt import QApplication, QAction, QMessageBox, QDialog, Qt, QMenu,\
    QIcon, QPixmap, QTreeWidget, QVBoxLayout, QTreeWidgetItem, QTextEdit, QDockWidget
from PyQt5 import QtCore, QtGui

# Calibre libraries
from calibre.gui2 import error_dialog
from calibre.gui2.tweak_book.plugin import Tool
from calibre.utils.config import JSONConfig, config_dir
from calibre.constants import iswindows, islinux, isosx, numeric_version
from calibre.ebooks.BeautifulSoup import BeautifulSoup

# Standard libraries
import os, sys, tempfile, webbrowser, shutil, json
import os.path
from os.path import expanduser, basename

# Load translation files (.mo) on the folder 'translations'
load_translations()

# DiapDealer's temp folder code
from contextlib import contextmanager

# Get config
import calibre_plugins.ACE.config as cfg


# Create a temp directory
@contextmanager
def make_temp_directory():
    import tempfile
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


# Set up icon
def get_icon(icon_name):
    # Check to see whether the icon exists as a Calibre resource
    # This will enable skinning if the user stores icons within a folder like:
    # ...\AppData\Roaming\calibre\resources\images\Plugin Name\
    icon_path = os.path.join(config_dir, 'resources', 'images', 'ACE',
                             icon_name.replace('images/', ''))
    if os.path.exists(icon_path):
        pixmap = QPixmap()
        pixmap.load(icon_path)
        return QIcon(pixmap)
    # As we did not find an icon elsewhere, look within our zip resources
    return get_icons(icon_name)


# Get equivalent ARIA role
def getrole(epub_type):
    noequiv = {
    'figure' : 'figure',
    'glossterm' : 'term',
    'glossdef' : 'definition',
    'landmarks' : 'directory',
    'list' : 'list',
    'list-item' : 'listitem',
    'page-list' : 'doc-pagelist',
    'referrer' : 'doc-backlink',
    'table' : 'table',
    'table-row' : 'row',
    'table-cell' : 'cell',
    }
    if epub_type in ['abstract', 'acknowledgments', 'afterword', 'appendix',
        'biblioentry', 'bibliography', 'biblioref', 'chapter', 'colophon', 'conclusion',
        'cover', 'credit', 'credits', 'dedication', 'endnote', 'endnotes', 'epigraph',
        'epilogue', 'errata', 'footnote', 'foreword', 'glossary', 'glossref', 'index',
        'introduction', 'noteref', 'notice', 'pagebreak', 'part', 'preface', 'prologue',
        'pullquote', 'qna', 'backlink', 'subtitle', 'tip', 'toc']:
        role = 'doc-' + epub_type
    elif epub_type in noequiv:
        role = noequiv[epub_type]
    else:
        role = None
    return role


# Simple wrapper for ACE
def ace_wrapper(*args):
    import subprocess
    startupinfo = None
    if islinux:
        process = subprocess.Popen(list(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   startupinfo=startupinfo, shell=False)
    else:
        process = subprocess.Popen(list(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   startupinfo=startupinfo, shell=True)
        # Stop the windows console popping up every time the program is run
        if iswindows:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
    ret = process.communicate()
    return_code = process.returncode
    return ret, return_code


# Main Class
class AceTool(Tool):
    
    # Set this to a unique name it will be used as a key
    name = 'ace'
    # If True the user can choose to place this tool in the plugins toolbar
    allowed_in_toolbar = True
    # If True the user can choose to place this tool in the plugins menu
    allowed_in_menu = True

    # Set up the config dialog inside the Editor
    def do_config(self):
        from calibre.gui2.widgets2 import Dialog
        from calibre.gui2.tweak_book import tprefs
        from PyQt5.Qt import QVBoxLayout, QDialogButtonBox
        from calibre_plugins.ACE.config import ConfigWidget
        tool = self

        class ConfigDialog(Dialog):

            def __init__(self):
                Dialog.__init__(self, _('Configure ACE'), 'plugin-ace-config-dialog', parent=tool.gui, prefs=tprefs)

            def setup_ui(self):
                self.box = QVBoxLayout(self)
                self.widget = ConfigWidget(self)
                self.box.addWidget(self.widget)
                self.button = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
                self.box.addWidget(self.button)
                self.button.accepted.connect(self.accept)
                self.button.rejected.connect(self.reject)

            def accept(self):
                if self.widget.validate():
                    self.widget.save_settings()
                    Dialog.accept(self)

        d = ConfigDialog()
        d.exec_()

    # Set up toolbars
    def create_action(self, for_toolbar=True):
        # Create an action, this will be added to the plugins toolbar and
        # the plugins menu
        ac = QAction(get_icon('images/icon.png'), _('Run ACE'), self.gui)
        if not for_toolbar:
            # Register a keyboard shortcut for this toolbar action. We only
            # register it for the action created for the menu, not the toolbar,
            # to avoid a double trigger
            self.register_shortcut(ac, 'ACE-tool', default_keys=('Ctrl+Shift+Alt+A',))

        # Check calibre version. 'Dialog' module in do_config()
        # is not available before version 2.15.0
        if numeric_version < (2, 15, 0):
            pass
        else:
            menu = QMenu()
            ac.setMenu(menu)
            config_menu_item = menu.addAction(_('Configure'))
            config_menu_item.setIcon(QIcon(I('config.png')))
            config_menu_item.setStatusTip(_('Configure ACE plugin'))
            config_menu_item.triggered.connect(self.do_config)

        ac.triggered.connect(self.run)
        return ac

    # Main routine
    def run(self):
        # Get preferences
        open_report = cfg.plugin_prefs['open_report']
        report_path = cfg.plugin_prefs['report_path']
        debug_mode = cfg.plugin_prefs['debug_mode']
        close_docks = cfg.plugin_prefs['close_docks']

        # Create a savepoint
        self.boss.add_savepoint(_('Before: ACE'))

        # Check file type
        book_type = self.current_container.book_type
        if book_type != 'epub':
            QMessageBox.information(self.gui, _('Unsupported file format'),
                                    _('You can\'t check {} files with ACE.').format(book_type))
            return

        # Create temp directory and Run ACE
        with make_temp_directory() as td:
            # Write current container to temporary epub
            epub_path = os.path.join(td, 'temp.epub')
            report_folder = os.path.join(report_path, 'report')
            report_data = os.path.join(report_folder, 'data')
            report_file_name = os.path.join(report_folder, 'report.html')
            json_file_name = report_file_name.replace('.html', '.json')
            if os.path.exists(report_data):
                shutil.rmtree(report_data)
            self.boss.commit_all_editors_to_container()
            self.current_container.commit(epub_path)

            # Define ACE command line parameters
            args = ['ace', '-f', '-o', report_folder, epub_path]

            # --------------------------------------------------------------------
            # create a dictionary that maps names to relative hrefs
            # --------------------------------------------------------------------
            epub_mime_map = self.current_container.mime_map
            epub_name_to_href = {}
            for href in epub_mime_map:
                epub_name_to_href[os.path.basename(href)] = href

            # Run ACE and handle errors
            try:
                # Display busy cursor
                QApplication.setOverrideCursor(Qt.WaitCursor)

                # Run ACE
                result, return_code = ace_wrapper(*args)
                stdout = result[0]
                stderr = result[1]

                # Full debug mode (complete log)
                if debug_mode:
                    stdout += stderr
                    QApplication.clipboard().setText(stdout)

                if return_code == 1:
                    # Hide busy cursor
                    QApplication.restoreOverrideCursor()

                    # If an error is found
                    QMessageBox.warning(self.gui, _('Error'), stderr)

                    # Ask user to rerun ACE
                    rerun_msg = _('ACE found an error during execution.' \
                                '\nDo you want to try to rerun it?' \
                                '\nThis can resolve a few errors.')
                    reply = QMessageBox.question(self.gui, _('Rerun'), rerun_msg,
                                                 QMessageBox.Yes, QMessageBox.No)
                    if reply == QMessageBox.Yes:
                        # Display busy cursor
                        QApplication.setOverrideCursor(Qt.WaitCursor)

                        # Rerun ACE
                        result, return_code = ace_wrapper(*args)
                        stdout = result[0]
                        stderr = result[1]

                        # Full debug mode (complete log)
                        if debug_mode:
                            stdout += stderr
                            QApplication.clipboard().setText(stdout)

                        if return_code == 1:
                            # Hide busy cursor
                            QApplication.restoreOverrideCursor()

                            # Exit if error persists
                            QMessageBox.critical(self.gui, _('Error'), stderr)
                            return
                    else:
                        return

                # If ACE succeeded, there should be a report file in the home folder
                if os.path.isfile(report_file_name):
                    with open(json_file_name, 'r') as file:
                        json_string = file.read()
                    parsed_json = json.loads(json_string)
                    earl_outcome = parsed_json['earl:result']['earl:outcome']

                    # Main routine
                    error_messages = []

                    if earl_outcome == 'fail':
                        for assertion in parsed_json['assertions']:

                            # Get file name
                            file_name = assertion['earl:testSubject']['url']

                            # Process all ACE assertions
                            for earl_assertion in assertion['assertions']:
                                epubcfi = None

                                # Get error message
                                error_message = (earl_assertion['earl:result']['dct:description'] + '.')\
                                    .replace('Fix any of the following:\n ', '')\
                                    .replace('Fix all of the following:\n ', '').replace('\n', '.').strip()

                                # Get error level (serious, moderate, minor)
                                error_level = earl_assertion['earl:test']['earl:impact']

                                # Define message type
                                if error_level == 'serious':
                                    restype = 'error'
                                elif error_level == 'moderate':
                                    restype = 'warning'
                                else:
                                    restype = 'info'

                                # Get epubcfi
                                if 'earl:pointer' in earl_assertion['earl:result']:
                                    epubcfi = earl_assertion['earl:result']['earl:pointer']['cfi'][0]
                                else:
                                    # ACE doesn't report line numbers for non-HTML files
                                    epubcfi = '/2'

                                # Get html (snippet) and recommended ARIA role
                                if 'html' in earl_assertion['earl:result']:
                                    role = None
                                    snippet = earl_assertion['earl:result']['html']
                                    soup = BeautifulSoup(snippet)
                                    tag = soup.contents[0]

                                    if tag.has_key('epub:type'):
                                        epub_type = tag['epub:type']
                                        role = getrole(epub_type)

                                # Add suggested role:
                                if error_message == 'Element has no ARIA role matching its epub:type.' and role is not None:
                                    error_message += ' Matching role: ' + role + '.'

                                # Save error information in list
                                error_messages.append((error_message, restype, file_name))

                                # Function to jump to the line corresponding to a partial cfi
                                def GotoLine():
                                    # Get the current line for the widget
                                    selected_item = tree.currentItem()
                                    current_row = tree.indexOfTopLevelItem(selected_item)
                                    # Get error information
                                    message, restype, file_name = error_messages[current_row]
                                    # Jump to line
                                    file_name = os.path.basename(file_name)
                                    filepath = epub_name_to_href[file_name]
                                    if numeric_version < (3, 38, 0):
                                        self.boss.edit_file(filepath, 'html')
                                    else:
                                        self.boss.show_partial_cfi_in_editor(filepath, epubcfi)

                                # Remove existing Ace/EpubCheck docks and close Check Ebook dock
                                for widget in self.gui.children():
                                    if isinstance(widget, QDockWidget) and widget.objectName() == 'ace-dock':
                                        widget.setParent(None)
                                    if close_docks:
                                        if isinstance(widget, QDockWidget) and widget.objectName()\
                                                in ('check-book-dock', 'epubcheck-dock'):
                                            widget.close()

                                # Define dock widget layout
                                tree = QTreeWidget()
                                tree.setRootIsDecorated(False)
                                l = QVBoxLayout()
                                l.addWidget(tree)
                                dock_widget = QDockWidget(self.gui)
                                dock_widget.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea |
                                                            Qt.BottomDockWidgetArea | Qt.TopDockWidgetArea)
                                dock_widget.setObjectName('ace-dock')
                                dock_widget.setWindowTitle('ACE, by Daisy')
                                dock_widget.setWidget(tree)
                                tree.setHeaderLabels([_('File'), _('Error message')])

                                # Add error messages to list widget
                                for error_msg in error_messages:
                                    message, restype, file_name = error_msg
                                    item = QTreeWidgetItem(tree, [file_name, message])
                                    # Select background color based on severity
                                    if restype == 'error':
                                        bg_color = QtGui.QBrush(QtGui.QColor(255, 230, 230))
                                    elif restype == 'warning':
                                        bg_color = QtGui.QBrush(QtGui.QColor(255, 255, 230))
                                    else:
                                        bg_color = QtGui.QBrush(QtGui.QColor(224, 255, 255))
                                    item.setBackground(0, QtGui.QColor(bg_color))
                                    item.setBackground(1, QtGui.QColor(bg_color))
                                    tree.addTopLevelItem(item)

                                tree.itemClicked.connect(GotoLine)

                                # Add dock widget to the dock
                                self.gui.addDockWidget(Qt.TopDockWidgetArea, dock_widget)

                                # Auto adjust column sizes
                                tree.resizeColumnToContents(0)

                    else:
                        # Hide busy cursor
                        QApplication.restoreOverrideCursor()

                        no_error_msg = _('ACE check is finished!'
                                         '\nCongratulations: no errors were found!')
                        QMessageBox.information(self.gui, 'ACE, by Daisy', no_error_msg)

                else:

                    # Hide busy cursor
                    QApplication.restoreOverrideCursor()

                    # If, for some reason, the report can't be found
                    import traceback
                    error_dialog(self.gui, _('Error opening the report'),
                                 _('Ace could not open the report. Click \'Show details\' for more info.'),
                                 det_msg=traceback.format_exc(), show=True)
                    return

            except:

                # Hide busy cursor
                QApplication.restoreOverrideCursor()

                # Exit if an unexpected error occurs, and report the error to the user
                import traceback
                error_dialog(self.gui, _('Unhandled exception'),
                             _('An unexpected error occurred. Click \'Show details\' for more info.'),
                             det_msg=traceback.format_exc(), show=True)
                return

        # Hide busy cursor
        QApplication.restoreOverrideCursor()

        # Show report on default browser
        if open_report:
            url = 'file://' + os.path.abspath(report_file_name)
            webbrowser.open(url)
