@echo off
:: Mount plugin
py make_plugin.py

:: Remove cache folder
rmdir /s /q __pycache__

:: Override calibre language
set CALIBRE_OVERRIDE_LANG=es

:: Add plugin to calibre
calibre-customize -a ACE.zip

:: Starts calibre in debug mode
calibre-debug -g

:: Remove plugin from calibre
calibre-customize -r ACE
