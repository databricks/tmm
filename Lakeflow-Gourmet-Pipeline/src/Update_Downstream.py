# Databricks notebook source
import requests
import json
from datetime import datetime

# API endpoint
url = "https://example.com/"

# Data to be sent
payload = {
    "status": "DONE",
    "project": "FLAGSHIP",
    "timestamp": datetime.now().isoformat()
}

# Headers
headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer YOUR_API_KEY_HERE"
}

# Make the POST request
try:
    response = requests.post(url, data=json.dumps(payload), headers=headers)
    
    # Check if the request was successful
    if response.status_code == 200:
        print("Successfully sent request to example.com")
        #print("Response content:", response.text[:100] + "...") # Print first 100 characters
    else:
        print(f"Failed to send request. Status code: {response.status_code}")
        print("Response:", response.text)
except requests.exceptions.RequestException as e:
    print(f"An error occurred: {e}")
