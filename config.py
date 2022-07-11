# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)
import six

__license__   = 'GPL v3'
__copyright__ = '2018-2022, Thiago Oliveira'
__docformat__ = 'restructuredtext en'

# Standard libraries
import os
import locale

# PyQt libraries
try:
    from qt.core import (QApplication, QtCore, QWidget, QLabel, QLineEdit, QPushButton, QCheckBox,
                          QGroupBox, QVBoxLayout, QGridLayout, QComboBox, QMessageBox)
except ImportError:
    from PyQt5.Qt import (QApplication, QWidget, QLabel, QLineEdit, QPushButton, QCheckBox,
                          QGroupBox, QVBoxLayout, QGridLayout, QComboBox, QMessageBox)
    from PyQt5 import QtCore

# Get PyQt version
Qt_version = int(QtCore.PYQT_VERSION_STR[0])

# Calibre libraries
from calibre.utils.config import JSONConfig
from calibre.utils.filenames import expanduser
from calibre.gui2 import choose_dir, error_dialog
from calibre_plugins.ACE.__init__ import PLUGIN_NAME, PLUGIN_VERSION

# Load translation files (.mo) on the folder 'translations'
load_translations()

# Get user language
user_language = locale.getdefaultlocale()

# This is where all preferences for this plugin will be stored.
plugin_prefs = JSONConfig('plugins/ACE')

# Set default preferences
plugin_prefs.defaults['report_path'] = expanduser('~')
plugin_prefs.defaults['open_report'] = True
plugin_prefs.defaults['debug_mode'] = False
plugin_prefs.defaults['close_docks'] = True
plugin_prefs.defaults['user_lang'] = user_language[0]
plugin_prefs.defaults['split_lines'] = True


# Set up Config Dialog
class ConfigWidget(QWidget):

    def __init__(self, plugin_action):
        QWidget.__init__(self)
        self.plugin_action = plugin_action
        layout = QVBoxLayout(self)
        self.setLayout(layout)

        # --- Folder Options ---
        directory_group_box = QGroupBox(_('Report Folder:'), self)
        layout.addWidget(directory_group_box)
        directory_group_box_layout = QVBoxLayout()
        directory_group_box.setLayout(directory_group_box_layout)

        # Directory path Textbox
        # Load the textbox with the current preference setting
        self.directory_txtBox = QLineEdit(plugin_prefs['report_path'], self)
        self.directory_txtBox.setToolTip(_('Folder to save the report'))
        directory_group_box_layout.addWidget(self.directory_txtBox)
        self.directory_txtBox.setReadOnly(True)

        # Folder select button
        directory_button = QPushButton('&'+_('Select Report Folder'), self)
        directory_button.setToolTip(_('Select the folder where the report will be saved.'))
        directory_group_box_layout.addWidget(directory_button)
        # Connect button to the getDirectory function
        directory_button.clicked.connect(self.get_directory)

        # --- Misc Options ---
        misc_group_box = QGroupBox(_('Options:'), self)
        layout.addWidget(misc_group_box)
        misc_group_box_layout = QVBoxLayout()
        misc_group_box.setLayout(misc_group_box_layout)

        # Open report checkbox
        self.open_report_check = QCheckBox('&'+_('Open Report after checking'), self)
        self.open_report_check.setToolTip(_('Check it to open the html report on you default browser.'))
        misc_group_box_layout.addWidget(self.open_report_check)
        # Load the checkbox with the current preference setting
        self.open_report_check.setChecked(plugin_prefs['open_report'])

        # Debug checkbox
        self.debug_mode_check = QCheckBox('&'+_('Debug Mode'), self)
        self.debug_mode_check.setToolTip(_('When checked, ACE log will be saved to clipboard.'))
        misc_group_box_layout.addWidget(self.debug_mode_check)
        # Load the checkbox with the current preference setting
        self.debug_mode_check.setChecked(plugin_prefs['debug_mode'])

        # Close docks checkbox
        self.close_docks_check = QCheckBox('&'+_('Close Validation Docks'), self)
        self.close_docks_check.setToolTip(_('When checked, ACE will attempt to close other validation docks.'))
        misc_group_box_layout.addWidget(self.close_docks_check)
        # Load the checkbox with the current preference setting
        self.close_docks_check.setChecked(plugin_prefs['close_docks'])

        # Split errors across multiple lines, when AXE give "Fix any/all of the following" messages
        self.split_lines_check = QCheckBox(_('Split multiline &errors'), self)
        self.split_lines_check.setToolTip(_('When checked, ACE will split multiline error messages.'))
        misc_group_box_layout.addWidget(self.split_lines_check)
        # Load the checkbox with the current preference setting
        self.split_lines_check.setChecked(plugin_prefs['split_lines'])

        # --- Lang Options ---
        lang_group_box = QGroupBox(_('Messages:'), self)
        layout.addWidget(lang_group_box)
        lang_group_box_layout = QGridLayout()
        lang_group_box.setLayout(lang_group_box_layout)

        # Language combobox
        self.language_box_label = QLabel(_('&Language:'), self)
        tooltip = _('Choose the language to show ACE and AXE messages. '
                    'Some languages work for AXE, but not for ACE.')
        self.language_box_label.setToolTip(tooltip)
        self.language_box = QComboBox()
        self.language_box.setToolTip(tooltip)
        self.language_box.addItems({'da', 'de', 'en', 'es', 'fr', 'ja', 'nl', 'pt_BR'})
        self.language_box.model().sort(0)
        self.language_box_label.setBuddy(self.language_box)
        lang_group_box_layout.addWidget(self.language_box_label, 0, 0)
        lang_group_box_layout.addWidget(self.language_box, 0, 1)
        # Load the combobox with the current preference setting
        default_index = self.language_box.findText(plugin_prefs['user_lang'])
        # Check if the user language is available. If not, fallbacks to English.
        if default_index == -1:
            self.language_box.setCurrentText('en')
        else:
            self.language_box.setCurrentIndex(default_index)

        # About button
        self.about_button = QPushButton(_('About'), self)
        self.about_button.clicked.connect(self.about)
        # about_group_box_layout.addWidget(self.about_button)
        layout.addWidget(self.about_button)

    def about(self):
        # About text
        text = _('This plugin is based on Doitsu\'s code for\n'
                 'Sigil\'s ACE Plugin and EPUBCheck for calibre.\n') +\
               '\n' +\
               _('The Config Menu is based on KindleUnpack.\n') +\
               '\n' +\
               _('Thanks to Kovid Goyal for adding the feature\n'
                 'that made possible linked error messages.')
        QMessageBox.about(self, PLUGIN_NAME + ' v' + PLUGIN_VERSION, text)

    def save_settings(self):
        # Save current dialog settings back to JSON config file
        plugin_prefs['report_path'] = six.text_type(self.directory_txtBox.displayText())
        plugin_prefs['open_report'] = self.open_report_check.isChecked()
        plugin_prefs['debug_mode'] = self.debug_mode_check.isChecked()
        plugin_prefs['close_docks'] = self.close_docks_check.isChecked()
        plugin_prefs['user_lang'] = self.language_box.currentText()
        plugin_prefs['split_lines'] = self.split_lines_check.isChecked()

    def get_directory(self):
        c = choose_dir(self, PLUGIN_NAME + 'dir_chooser',
                       _('Select Directory to save Report to'))
        if c:
            self.directory_txtBox.setReadOnly(False)
            self.directory_txtBox.setText(c)
            self.directory_txtBox.setReadOnly(True)

    def validate(self):
        # This is just to catch the situation where someone might
        # manually enter a non-existent path in the Default path textbox.
        # Shouldn't be possible at this point.
        if not os.path.exists(self.directory_txtBox.text()):
            errmsg = _('<p>The path specified for the Report Folder does not exist.'
                       '<br/>Your latest preference changes will <b>NOT</b> be saved!</p>')
            error_dialog(None, PLUGIN_NAME + ' v' + PLUGIN_VERSION,
                         errmsg, show=True)
            return False
        return True
