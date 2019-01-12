@echo off
:: Extract translatable strings from source files
py %localappdata%\Programs\Python\Python37\Tools\i18n\pygettext.py __init__.py config.py main.py

:: Move the generated file to translations folder
move messages.pot translations > nul
