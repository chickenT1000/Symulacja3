@echo off
REM Setup Python venv and start the Flask server on port 8080

IF NOT EXIST venv (
  echo Creating virtual environment...
  python -m venv venv
)

echo Activating virtual environment...
call venv\Scripts\activate

echo Installing/updating dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt

echo Starting Flask server on port 8080...
start "" http://localhost:8080

echo Server starting... Press Ctrl+C to stop
python app.py
