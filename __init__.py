#!/usr/bin/env python2
# vim:fileencoding=utf-8

from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__ = 'GPL v3'
__copyright__ = '2018-2022, Thiago Oliveira'
__docformat__ = 'restructuredtext en'

# Calibre libraries
from calibre.customize import EditBookToolPlugin, InterfaceActionBase

# Load translation files (.mo) on the folder 'translations'
load_translations()

PLUGIN_NAME          = 'ACE'
PLUGIN_DESCRIPTION   = _('Checks the accessibility of EPUB files with ACE.')
PLUGIN_VERSION_TUPLE = (1, 1, 6)
PLUGIN_VERSION       = '.'.join([str(x) for x in PLUGIN_VERSION_TUPLE])
PLUGIN_AUTHOR        = 'Thiago Oliveira'


class AcePlugin(EditBookToolPlugin):

    name                    = PLUGIN_NAME
    description             = PLUGIN_DESCRIPTION
    supported_platforms     = ['windows', 'osx', 'linux']
    author                  = PLUGIN_AUTHOR
    version                 = PLUGIN_VERSION_TUPLE
    minimum_calibre_version = (2, 0, 0)

    #: This field defines the GUI plugin class that contains all the code
    #: that actually does something. Its format is module_path:class_name
    #: The specified class must be defined in the specified module.
    actual_plugin           = 'calibre_plugins.ACE.main:AceTool'

    def is_customizable(self):
        '''
        This method must return True to enable customization via
        Preferences->Plugins
        '''
        return True

    def config_widget(self):
        '''
        Implement this method and :meth:`save_settings` in your plugin to
        use a custom configuration dialog.

        This method, if implemented, must return a QWidget. The widget can have
        an optional method validate() that takes no arguments and is called
        immediately after the user clicks OK. Changes are applied if and only
        if the method returns True.

        If for some reason you cannot perform the configuration at this time,
        return a tuple of two strings (message, details), these will be
        displayed as a warning dialog to the user and the process will be
        aborted.

        The base class implementation of this method raises NotImplementedError
        so by default no user configuration is possible.
        '''
        from calibre_plugins.ACE.config import ConfigWidget
        return ConfigWidget(self.actual_plugin)

    def save_settings(self, config_widget):
        '''
        Save the settings specified by the user with config_widget.

        :param config_widget: The widget returned by :meth:`config_widget`.
        '''
        config_widget.save_settings()
