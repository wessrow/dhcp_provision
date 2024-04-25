"""
Setup for GUNICORN
"""

# pylint: disable=invalid-name

timeout = 1500
bind = "0.0.0.0:5005"
workers = 8
certfile = "cert.pem"
keyfile = "key.pem"
