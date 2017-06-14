import os
from app import create_app

app = create_app(os.getenv('DO_CONFIG') or 'default')
