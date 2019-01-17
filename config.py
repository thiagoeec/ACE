# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2018, Thiago Oliveira'
__docformat__ = 'restructuredtext en'

# Standard libraries
import os

# PyQt libraries
from PyQt5.Qt import (QWidget, QLabel, QLineEdit, QPushButton, QCheckBox,
                      QGroupBox, QVBoxLayout, QComboBox, QMessageBox)

# Calibre libraries
from calibre.utils.config import JSONConfig
from calibre.utils.filenames import expanduser
from calibre.gui2 import choose_dir, error_dialog
from calibre_plugins.ACE.__init__ import PLUGIN_NAME, PLUGIN_VERSION

# Load translation files (.mo) on the folder 'translations'
load_translations()

# This is where all preferences for this plugin will be stored.
plugin_prefs = JSONConfig('plugins/ACE')

# Set default preferences
plugin_prefs.defaults['report_path'] = expanduser('~')
plugin_prefs.defaults['open_report'] = True
plugin_prefs.defaults['debug_mode'] = False
plugin_prefs.defaults['close_docks'] = True


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
        directory_button = QPushButton(_('Select Report Folder'), self)
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
        self.open_report_check = QCheckBox(_('Open Report after checking'), self)
        self.open_report_check.setToolTip(_('Check it to open the html report on you default browser.'))
        misc_group_box_layout.addWidget(self.open_report_check)
        # Load the checkbox with the current preference setting
        self.open_report_check.setChecked(plugin_prefs['open_report'])

        # Debug checkbox
        self.debug_mode_check = QCheckBox(_('Debug Mode'), self)
        self.debug_mode_check.setToolTip(_('When checked, ACE log will be saved to clipboard.'))
        misc_group_box_layout.addWidget(self.debug_mode_check)
        # Load the checkbox with the current preference setting
        self.debug_mode_check.setChecked(plugin_prefs['debug_mode'])

        # Close docks checkbox
        self.close_docks_check = QCheckBox(_('Close Validation Docks'), self)
        self.close_docks_check.setToolTip(_('When checked, ACE will attempt to close other validation docks.'))
        misc_group_box_layout.addWidget(self.close_docks_check)
        # Load the checkbox with the current preference setting
        self.close_docks_check.setChecked(plugin_prefs['close_docks'])

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
                 'that make possible linked error messages.')
        QMessageBox.about(self, _('About the ACE plugin'), text.decode('utf-8'))

    def save_settings(self):
        # Save current dialog settings back to JSON config file
        plugin_prefs['report_path'] = unicode(self.directory_txtBox.displayText())
        plugin_prefs['open_report'] = self.open_report_check.isChecked()
        plugin_prefs['debug_mode'] = self.debug_mode_check.isChecked()
        plugin_prefs['close_docks'] = self.close_docks_check.isChecked()

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
