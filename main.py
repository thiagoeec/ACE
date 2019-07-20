#!/usr/bin/env python2
# vim:fileencoding=utf-8

from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__ = 'GPL v3'
__copyright__ = '2018, Thiago Oliveira'
__docformat__ = 'restructuredtext en'

# Standard libraries
import os
import os.path
import sys
import tempfile
import webbrowser
import shutil
import json
from os.path import expanduser, basename

# PyQt libraries
from PyQt5.Qt import QApplication, QAction, QMessageBox, QDialog, Qt, QMenu, QIcon,\
    QPixmap, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QTextEdit, QDockWidget
from PyQt5 import QtCore, QtGui

# Calibre libraries
from calibre.gui2 import error_dialog
from calibre.gui2.tweak_book.plugin import Tool
from calibre.utils.config import JSONConfig, config_dir
from calibre.constants import iswindows, islinux, isosx, numeric_version
from calibre.ebooks.BeautifulSoup import BeautifulSoup, BeautifulStoneSoup

# DiapDealer's temp folder code
from contextlib import contextmanager

# Get config
import calibre_plugins.ACE.config as cfg

# Load translation files (.mo) on the folder 'translations'
load_translations()


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
        'figure': 'figure', 'glossterm': 'term', 'glossdef': 'definition', 'landmarks': 'directory',
        'list': 'list', 'list-item': 'listitem', 'page-list': 'doc-pagelist', 'referrer': 'doc-backlink',
        'table': 'table', 'table-row': 'row', 'table-cell': 'cell',
    }
    if epub_type in [
        'abstract', 'acknowledgments', 'afterword', 'appendix', 'biblioentry', 'bibliography',
        'biblioref', 'chapter', 'colophon', 'conclusion', 'cover', 'credit', 'credits', 'dedication',
        'endnote', 'endnotes', 'epigraph', 'epilogue', 'errata', 'footnote', 'foreword', 'glossary',
        'glossref', 'index', 'introduction', 'noteref', 'notice', 'pagebreak', 'part', 'preface',
        'prologue', 'pullquote', 'qna', 'backlink', 'subtitle', 'tip', 'toc'
    ]:
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
        from PyQt5.Qt import QDialogButtonBox
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
        user_lang = cfg.plugin_prefs['user_lang']

        # Create a savepoint
        try:
            self.boss.add_savepoint(_('Before: ACE'))
        except AttributeError:
            QMessageBox.information(self.gui, _('Empty Editor'),
                                    _('You must first open a book!'))
            return

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
            args = ['ace', '-f', '-o', report_folder, '-l', user_lang, epub_path]

            # Create a dictionary that maps names to relative hrefs
            epub_mime_map = self.current_container.mime_map
            epub_name_to_href = {}
            for href in epub_mime_map:
                epub_name_to_href[os.path.basename(href)] = href

            # Run ACE and handle errors
            try:
                # Display busy cursor
                QApplication.setOverrideCursor(Qt.WaitCursor)

                self.gui.show_status_message(_("Checking book..."), 5)

                # Run ACE
                result, return_code = ace_wrapper(*args)
                stdout = result[0]
                stderr = result[1]

                # Debug mode (ACE log)
                if debug_mode:
                    stdout += stderr
                    QApplication.clipboard().setText(stdout)

                if return_code == 1:
                    # Hide busy cursor
                    QApplication.restoreOverrideCursor()

                    # If an error is found
                    QMessageBox.warning(self.gui, _('Error'), stderr)

                    # Ask user to rerun ACE
                    rerun_msg = _('ACE found an error during execution.'
                                  '\nDo you want to try to rerun it?'
                                  '\nThis can resolve a few errors.')
                    reply = QMessageBox.question(self.gui, _('Rerun'), rerun_msg,
                                                 QMessageBox.Yes, QMessageBox.No)
                    if reply == QMessageBox.Yes:
                        # Display busy cursor
                        QApplication.setOverrideCursor(Qt.WaitCursor)

                        self.gui.show_status_message(_("Checking book..."), 5)

                        # Rerun ACE
                        result, return_code = ace_wrapper(*args)
                        stdout = result[0]
                        stderr = result[1]

                        # Debug mode (ACE log)
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

                    # Parse JSON report file
                    error_messages = []
                    msg_index = 0

                    if earl_outcome == 'fail':
                        for assertion in parsed_json['assertions']:

                            # Get file name
                            file_name = assertion['earl:testSubject']['url']

                            # Process all ACE assertions
                            for earl_assertion in assertion['assertions']:

                                # Get error message
                                error_message = (earl_assertion['earl:result']['dct:description'] + '.')\
                                    .replace('\n\n', '. ').replace(':\n', ':').replace('\n', ';').strip()

                                # Get error level (critical, serious, moderate, minor) and id
                                error_level = earl_assertion['earl:test']['earl:impact']
                                error_id = earl_assertion['earl:test']['dct:title']

                                # Get epubcfi
                                if 'earl:pointer' in earl_assertion['earl:result']:
                                    epubcfi = earl_assertion['earl:result']['earl:pointer']['cfi'][0]
                                else:
                                    # ACE doesn't report line numbers for non-HTML files
                                    epubcfi = '/2'

                                # Get html (snippet) and recommended ARIA role
                                roles = []
                                if 'html' in earl_assertion['earl:result']:
                                    snippet = earl_assertion['earl:result']['html']
                                    if numeric_version < (3, 41, 0):
                                        soup = BeautifulSoup(snippet)
                                        tag = soup.contents[0]
                                        if tag.has_key('epub:type'):
                                            epub_type = tag['epub:type']
                                            epub_type_list = epub_type.split()
                                            for epub_type_item in epub_type_list:
                                                roles.append(getrole(epub_type_item))
                                    else:
                                        soup = BeautifulStoneSoup(snippet)
                                        tag = soup.contents[0]
                                        if 'epub:type' in tag.attrs:
                                            epub_type = tag['epub:type']
                                            epub_type_list = epub_type.split()
                                            for epub_type_item in epub_type_list:
                                                roles.append(getrole(epub_type_item))

                                # Add suggested role:
                                if error_id == 'epub-type-has-matching-role' and roles is not []:
                                    role_string = None
                                    multiple_roles_msg = ''
                                    for role in roles:
                                        if role is not None:
                                            if role_string is None:
                                                role_string = role
                                            else:
                                                role_string = role_string + ', ' + role
                                                multiple_roles_msg = _(' (you must use only one role)')
                                    error_message += _(' Matching ARIA role: ') + role_string + multiple_roles_msg + '.'

                                # Save error information in a list
                                error_messages.append((msg_index, error_message, error_level, file_name, epubcfi))

                                # Message index to help sorting
                                msg_index = msg_index + 1

                    else:
                        # Hide busy cursor
                        QApplication.restoreOverrideCursor()

                        no_error_msg = _('ACE check is finished!'
                                         '\nCongratulations: no errors were found!')
                        QMessageBox.information(self.gui, 'ACE, by Daisy', no_error_msg)

                        # Show report on default browser
                        if open_report:
                            url = 'file://' + os.path.abspath(report_file_name)
                            webbrowser.open(url)

                        return

                else:

                    # Hide busy cursor
                    QApplication.restoreOverrideCursor()

                    # If, for some reason, the report can't be found
                    import traceback
                    error_dialog(self.gui, _('Error opening the report'),
                                 _('Ace could not open the report. Click \'Show details\' for more info.'),
                                 det_msg=traceback.format_exc(), show=True)
                    return

                # Go to the error line
                def go_to_line():

                    # Parse the CFI reference
                    def decode_cfi(root, cfi):
                        from lxml.etree import XPathEvalError
                        from calibre.ebooks.epub.cfi.parse import parser, get_steps
                        p = parser()
                        try:
                            pcfi = p.parse_path(cfi)[0]
                        except Exception:
                            import traceback
                            traceback.print_exc()
                            return
                        if not pcfi:
                            import sys
                            print('Failed to parse CFI: %r' % pcfi, file=sys.stderr)
                            return
                        steps = get_steps(pcfi)
                        ans = root
                        for step in steps:
                            num = step.get('num', 0)
                            node_id = step.get('id')
                            try:
                                match = ans.xpath('descendant::*[@id="%s"]' % node_id)
                            except XPathEvalError:
                                match = ()
                            if match:
                                ans = match[0]
                                continue
                            index = 0
                            for child in ans.iterchildren('*'):
                                index |= 1  # increment index by 1 if it is even
                                index += 1
                                if index == num:
                                    ans = child
                                    break
                            else:
                                return
                        return ans

                    # Jump to the line corresponding to a partial CFI ref
                    def show_partial_cfi_in_editor(name, cfi):
                        editor = self.boss.edit_file(name)
                        if not editor or not editor.has_line_numbers:
                            return False
                        from calibre.ebooks.oeb.polish.parsing import parse
                        root = parse(
                            editor.get_raw_data(), decoder=lambda x: x.decode('utf-8'),
                            line_numbers=True, linenumber_attribute='data-lnum')
                        node = decode_cfi(root, cfi)
                        if node is not None:
                            lnum = node.get('data-lnum')
                            if lnum:
                                lnum = int(lnum)
                                editor.current_line = lnum
                                return True
                        return False

                    # Get the current line for the widget
                    selected_item = tree.currentItem()
                    # Read the msg_index (hidden column)
                    row_index = int(selected_item.text(0)) - 1

                    # Get error information
                    m_index, msg, sev, f_name, epub_cfi = error_messages[row_index]

                    # Jump to line
                    f_name = os.path.basename(f_name)
                    filepath = epub_name_to_href[f_name]
                    if os.path.splitext(filepath)[1] == '.opf':
                        self.boss.edit_file(filepath)  # .opf files does not support epubcfi
                    else:
                        if numeric_version < (3, 38, 0):
                            show_partial_cfi_in_editor(filepath, epub_cfi)
                        else:
                            self.boss.show_partial_cfi_in_editor(filepath, epub_cfi)

                # Remove existing Ace/EpubCheck docks and close Check Ebook dock
                for widget in self.gui.children():
                    if isinstance(widget, QDockWidget) and widget.objectName() == 'ace-dock':
                        widget.setParent(None)
                    if close_docks:
                        if isinstance(widget, QDockWidget) and widget.objectName() \
                                in ('check-book-dock', 'epubcheck-dock'):
                            widget.close()

                # Define dock widget layout
                tree = QTreeWidget()
                tree.setRootIsDecorated(False)
                layout = QVBoxLayout()
                layout.addWidget(tree)
                dock_widget = QDockWidget(self.gui)
                dock_widget.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea |
                                            Qt.BottomDockWidgetArea | Qt.TopDockWidgetArea)
                dock_widget.setObjectName('ace-dock')
                dock_widget.setWindowTitle('ACE, by Daisy')
                dock_widget.setWidget(tree)
                tree.setHeaderLabels(['Index', _('File'), _('Severity'), _('Error message')])
                header = tree.headerItem()
                header.setToolTip(1, _('Sort by Filename'))
                header.setToolTip(2, _('Sort by Severity'))
                header.setToolTip(3, _('Sort by Error Message'))

                # Add error messages to list widget
                for error_msg in error_messages:
                    msg_index, message, error_level, file_name, epubcfi = error_msg

                    # Set translatable severity type
                    if error_level == 'critical':
                        severity_type = _('Critical')
                    elif error_level == 'serious':
                        severity_type = _('Serious')
                    elif error_level == 'moderate':
                        severity_type = _('Moderate')
                    else:
                        severity_type = _('Minor')

                    msg_index = msg_index + 1
                    msg_index = "{0:0=3d}".format(msg_index)
                    item = QTreeWidgetItem(tree, [str(msg_index), os.path.split(file_name)[1], severity_type, message])
                    # Select background color based on severity
                    if error_level == 'critical':
                        bg_color = QtGui.QBrush(QtGui.QColor(255, 200, 200))
                    elif error_level == 'serious':
                        bg_color = QtGui.QBrush(QtGui.QColor(255, 220, 170))
                    elif error_level == 'moderate':
                        bg_color = QtGui.QBrush(QtGui.QColor(255, 255, 230))
                    else:
                        bg_color = QtGui.QBrush(QtGui.QColor(190, 255, 255))
                    item.setBackground(0, QtGui.QColor(bg_color))
                    item.setBackground(1, QtGui.QColor(bg_color))
                    item.setBackground(2, QtGui.QColor(bg_color))
                    item.setBackground(3, QtGui.QColor(bg_color))
                    tree.addTopLevelItem(item)

                tree.itemClicked.connect(go_to_line)

                # Double-click copies to clipboard
                def msg_to_clipboard():
                    item_content = _('File') + ': ' + tree.currentItem().text(1) + '\n' +\
                               _('Severity') + ': ' + tree.currentItem().text(2) + '\n' +\
                               _('Error message') + ': ' + tree.currentItem().text(3)
                    QApplication.clipboard().setText(item_content)

                tree.itemDoubleClicked.connect(msg_to_clipboard)

                # Add dock widget to the dock
                self.gui.addDockWidget(Qt.TopDockWidgetArea, dock_widget)

                # Auto adjust column sizes
                tree.resizeColumnToContents(0)
                tree.resizeColumnToContents(1)

                # Enable sorting
                tree.setSortingEnabled(True)
                tree.sortItems(0, Qt.AscendingOrder)
                tree.setColumnHidden(0, True)

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
