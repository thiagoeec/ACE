@echo off
:: Mount the final plugin file
py make_plugin.py

:: Remove the cache folder
rmdir /s /q __pycache__

:: Add ACE plugin to calibre
calibre-customize -a ACE.zip
