"""
Firebase Authentication utilities for backend
"""
import requests
from functools import wraps
from flask import request, jsonify
import os

# Firebase project ID (set as environment variable)
FIREBASE_PROJECT_ID = os.environ.get('FIREBASE_PROJECT_ID', 'roadwatch-kerala')

def verify_firebase_token(id_token):
    """
    Verify Firebase ID token
    Returns user data if valid, None if invalid
    """
    try:
        # Verify token using Firebase Auth REST API
        url = f'https://identitytoolkit.googleapis.com/v1/accounts:lookup?key={os.environ.get("FIREBASE_API_KEY")}'
        response = requests.post(url, json={'idToken': id_token})
        
        if response.status_code == 200:
            data = response.json()
            if 'users' in data and len(data['users']) > 0:
                user = data['users'][0]
                return {
                    'uid': user.get('localId'),
                    'email': user.get('email'),
                    'display_name': user.get('displayName'),
                    'photo_url': user.get('photoUrl'),
                    'email_verified': user.get('emailVerified', False)
                }
        
        return None
    except Exception as e:
        print(f"Error verifying Firebase token: {e}")
        return None


def require_auth(f):
    """
    Decorator to require authentication for API endpoints
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing or invalid authorization header'}), 401
        
        token = auth_header.split('Bearer ')[1]
        user_data = verify_firebase_token(token)
        
        if not user_data:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        # Attach user data to request for use in endpoint
        request.current_user = user_data
        return f(*args, **kwargs)
    
    return decorated_function


def optional_auth(f):
    """
    Decorator for endpoints that work with or without authentication
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split('Bearer ')[1]
            user_data = verify_firebase_token(token)
            request.current_user = user_data if user_data else None
        else:
            request.current_user = None
        
        return f(*args, **kwargs)
    
    return decorated_function
