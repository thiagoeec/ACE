#!/usr/bin/env python2
# vim:fileencoding=utf-8

from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__ = 'GPL v3'
__copyright__ = '2018, Thiago Oliveira'
__docformat__ = 'restructuredtext en'

# PyQt libraries
from PyQt5.Qt import QApplication, QAction, QMessageBox, QDialog, Qt, QMenu, QIcon, QPixmap

# Calibre libraries
from calibre.gui2 import error_dialog
from calibre.gui2.tweak_book.plugin import Tool
from calibre.utils.config import JSONConfig, config_dir
from calibre.constants import iswindows, islinux, isosx

# Standard libraries
import os, sys, tempfile, webbrowser, shutil
import os.path
from os.path import expanduser

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
        from calibre.constants import numeric_version as calibre_version
        if calibre_version < (2, 15, 0):
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
            if os.path.exists(report_data):
                shutil.rmtree(report_data)
            self.boss.commit_all_editors_to_container()
            self.current_container.commit(epub_path)

            # Define ACE command line parameters
            args = ['ace', '-f', '-o', report_folder, epub_path]

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

                # Hide busy cursor
                QApplication.restoreOverrideCursor()

                if return_code == 1:
                    # If an error is found
                    QMessageBox.warning(self.gui, _('Error'), stderr)

                    # Ask user to rerun ACE
                    from PyQt5 import QtGui
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

                        # Hide busy cursor
                        QApplication.restoreOverrideCursor()

                        if return_code == 1:
                            # Exit if error persists
                            QMessageBox.critical(self.gui, _('Error'), stderr)
                            return
                    else:
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

        # Show report on default browser
        if open_report:
            report_true_msg = _('ACE check is finished!' \
                              '\nThe report will open on your default browser.')
            QMessageBox.information(self.gui, 'ACE, by Daisy', report_true_msg)
            url = 'file://' + os.path.abspath(report_file_name)
            webbrowser.open(url)
        else:
            # Point report location
            report_false_msg = _('ACE check is finished!' \
                               '\nThe report was saved to: ')
            QMessageBox.information(self.gui, 'ACE, by Daisy', report_false_msg + '\'' + report_folder + '\'.')
