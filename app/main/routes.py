from flask import send_file
from . import main


@main.route('/')
def index():
    return send_file('templates/index.html')
