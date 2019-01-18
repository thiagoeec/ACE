@echo off
set PYTHONIOENCODING=UTF-8
setlocal enableDelayedExpansion

:: Fetch new translations (over 25% finished). Use -f to force download.
echo.
tx pull --minimum-perc=20 -a %1

:: Gererate .mo files from the .po files downloaded from Transifex
cd translations
echo.
for %%f in (*.po) do (
	for /f %%a in ('dir %%f^|find /i " %%f"') do (
		set FileDate=%%a
		if !FileDate! EQU !Date! (
			calibre-debug.exe -c "from calibre.translations.msgfmt import main; main()" %%~nf
			echo Converting %%f --^> %%~nf.mo 
		)
	)
)

cd ..
