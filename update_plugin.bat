@echo off
::Update "messages.pot" if argument "-m" is passed
if [%1]==[-m] (
	call create_pot_files.bat
)

::Pull new translations from Transifex. Use "-f" to force download.
call pull_translations.bat %2

::Assemble plugin file
echo.
call make_plugin.bat
