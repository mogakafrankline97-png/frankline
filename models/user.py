# models/user.py
import uuid
from datetime import datetime
import bcrypt
import requests
from config import Config

class User:
    def __init__(self, data):
        self.id = data.get('id')
        self.email = data.get('email')
        self.full_name = data.get('full_name')
        self.role = data.get('role', 'user')
        self.is_active = data.get('is_active', True)
        self.created_at = data.get('created_at')
        self.updated_at = data.get('updated_at')
        self.last_login = data.get('last_login')
        self.phone = data.get('phone')
        self.avatar_url = data.get('avatar_url')
        self.password_hash = data.get('password_hash')

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'full_name': self.full_name,
            'role': self.role,
            'is_active': self.is_active,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'last_login': self.last_login,
            'phone': self.phone,
            'avatar_url': self.avatar_url
        }

    @staticmethod
    def hash_password(password):
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    @staticmethod
    def verify_password(password, password_hash):
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))

    @staticmethod
    def get_by_email(email):
        try:
            response = requests.get(
                f"{Config.SUPABASE_URL}/rest/v1/users?email=eq.{email}&select=*",
                headers=Config.SUPABASE_HEADERS,
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if data:
                    return User(data[0])
            return None
        except Exception as e:
            print(f"Error getting user: {e}")
            return None

    @staticmethod
    def authenticate(email, password):
        user = User.get_by_email(email)
        if not user:
            return None, "User not found"
        
        if not user.is_active:
            return None, "Account is deactivated"
        
        if not User.verify_password(password, user.password_hash):
            return None, "Invalid password"
        
        # Update last_login
        try:
            requests.patch(
                f"{Config.SUPABASE_URL}/rest/v1/users?id=eq.{user.id}",
                headers=Config.SUPABASE_HEADERS,
                json={'last_login': datetime.utcnow().isoformat()},
                timeout=10
            )
        except:
            pass
        
        return user, None