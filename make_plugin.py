#!/usr/bin/python
# -*- coding: utf-8 -*-


__license__   = 'GPL v3'
__copyright__ = '2019, Thiago Oliveira'
__docformat__ = 'restructuredtext en'

from glob import glob

from make_zip import createZipFile

if __name__ == "__main__":
    
    filename = "ACE.zip"
    exclude = ['make_zip.py', 'make_plugin.py', '*.pot', '*.po', '*.md']
    # from top dir. 'w' for overwrite
    # from calibre-plugin dir. 'a' for append
    files = ['images', 'translations']
    files.extend(glob('*.py'))
    files.extend(glob('plugin-import-name-*.txt'))
    createZipFile(filename, "w", files, exclude=exclude)
