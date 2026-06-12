import sys
import os

# Insert the project path to the system path so Passenger can find app.py
sys.path.insert(0, os.path.dirname(__file__))

# Import the Flask app instance (named 'app' in app.py) and expose it as 'application'
from app import app as application
