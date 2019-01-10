@echo off
::Update "messages.pot"
call create_pot_files.bat

::Pull new translations from Transifex
call pull_translations.bat

::Assemble plugin file
call make_plugin.bat
