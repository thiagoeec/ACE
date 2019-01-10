@echo off
set PYTHONIOENCODING=UTF-8

:: Fetch new translations (over 25% finished)
tx.exe pull --minimum-perc=25 -f -a

:: Gererate .mo files from the .po files downloaded from Transifex
cd translations
for %%f in (*.po) do (
    "C:\Program Files\Calibre2\calibre-debug.exe" -c "from calibre.translations.msgfmt import main; main()" %%~nf
)

cd ..
