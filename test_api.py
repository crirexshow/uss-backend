#!/usr/bin/env python3

import requests
import json

def test_register_api():
    url = 'http://localhost:5000/api/auth/register'
    
    data = {
        'email': 'test@example.com',
        'password': 'password123',
        'tipo_utente': 'Promotore',
        'instagram_link': 'https://instagram.com/test_user'
    }
    
    headers = {
        'Content-Type': 'application/json'
    }
    
    try:
        print("Sending request to:", url)
        print("Data:", json.dumps(data, indent=2))
        
        response = requests.post(url, json=data, headers=headers)
        
        print(f"\nResponse Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Content: {response.text}")
        
        if response.text:
            try:
                json_response = response.json()
                print(f"Parsed JSON: {json.dumps(json_response, indent=2)}")
            except json.JSONDecodeError as e:
                print(f"Failed to parse JSON: {e}")
        else:
            print("Empty response body")
            
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")

if __name__ == '__main__':
    test_register_api()

