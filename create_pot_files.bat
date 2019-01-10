set PYTHONIOENCODING=UTF-8

for %%f in (*.py) do (
	set count=1
    py -3.7 "C:\Users\go_th\AppData\Local\Programs\Python\Python37\Tools\i18n\pygettext.py" -d message%%~nf %%~nf.py
	set count=count+1
)