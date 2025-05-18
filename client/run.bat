@echo off
echo Checking requirements...
python -m pip install --quiet --disable-pip-version-check -r requirements.txt

echo Launching client...
python client.py

pause
