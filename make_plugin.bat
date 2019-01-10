@echo off
:: Mount the final plugin file
py make_plugin.py

:: Removes the cache folder
rmdir /s /q __pycache__

:: Adds ACE plugin to calibre
calibre-customize -a ACE.zip
