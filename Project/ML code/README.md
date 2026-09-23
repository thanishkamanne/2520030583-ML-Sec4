# TrafficSense AI - Professional Frontend

This project adds a Flask web frontend to the supplied trained Random Forest model.

## Project structure

Traffic-ML-WebApp/
├── app.py
├── requirements.txt
├── model/
│   └── best_model.pkl
├── templates/
│   └── index.html
└── static/
    ├── style.css
    └── script.js

## Run in VS Code (Windows)

1. Extract the ZIP.
2. Open the `Traffic-ML-WebApp` folder in VS Code.
3. Open Terminal → New Terminal.
4. Create a virtual environment:

   `python -m venv venv`

5. Activate it:

   PowerShell:
   `venv\Scripts\Activate.ps1`

   Command Prompt:
   `venv\Scripts\activate`

6. Install packages:

   `pip install -r requirements.txt`

7. Start the website:

   `python app.py`

8. Open the URL shown in the terminal, normally:

   http://127.0.0.1:5000

## Important

The frontend uses the exact 9 input columns expected by the supplied `best_model.pkl`.

The model was trained with these user-facing fields:
- Date
- Timestamp
- Direction
- Day/Night
- Weather
- Start Frame
- Number of Frames

The categorical values are converted into the same one-hot columns used during model training.

The "Fill Sample Data" button uses an example taken from the supplied dataset. It is only for testing the interface.

If PowerShell blocks virtual-environment activation, run:
`Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`

Then activate the environment again.

Stop the server with Ctrl+C.
