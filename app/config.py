# app/config.py

import os

class Config:
    SQLALCHEMY_DATABASE_URI = "mysql://root:hazemshokry@localhost:3306/traindb2"
    SQLALCHEMY_TRACK_MODIFICATIONS = False