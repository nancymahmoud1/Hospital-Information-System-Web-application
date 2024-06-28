#!/bin/bash
cd /Users/yassientawfik/Documents/SBME/Semester04/Data_base/Project/Team_13_Hospital_Website
source venv/bin/activate
/Users/yassientawfik/Documents/SBME/Semester04/Data_base/Project/Team_13_Hospital_Website/venv/bin/python app.py & # Start the Flask app in the background
sleep 2 # Wait for a couple of seconds to ensure the server starts
open http://127.0.0.1:5000 # Open the browser to the specified URL
