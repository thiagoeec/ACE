@echo off
::Assemble plugin file
call make_plugin.bat

:: Override calibre with the language code passed
set CALIBRE_OVERRIDE_LANG=%1

:: Starts calibre in debug mode
calibre-debug -g

:: Remove plugin from calibre
calibre-customize -r ACE
