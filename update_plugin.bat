@echo off
::Update "messages.pot" if argument "-m" is passed
if [%1]==[-m] (
	call create_pot_files.bat
)

::Pull new translations from Transifex
call pull_translations.bat

::Assemble plugin file
echo.
call make_plugin.bat
