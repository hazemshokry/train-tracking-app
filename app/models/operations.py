# app/models/operations.py

from app.extensions import db
from datetime import datetime

class Operation(db.Model):
    __tablename__ = 'operations'
    
    id = db.Column(db.Integer, primary_key=True)
    train_number = db.Column(db.String(255), db.ForeignKey('trains.train_number'), nullable=False)
    operational_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(50), default='on time')  # Default status, can be updated
    total_delay = db.Column(db.Integer, default=0)  # Total delay in minutes
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    train = db.relationship('Train', backref='operations')

    def __repr__(self):
        return f"<Operation Train {self.train_number} Date {self.operational_date} Status {self.status}>"