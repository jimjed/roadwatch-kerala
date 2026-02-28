"""
Extended database models with user authentication
"""
from models import db, utc_now
from datetime import datetime, timezone
import json

class User(db.Model):
    """User account"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    firebase_uid = db.Column(db.String(128), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    display_name = db.Column(db.String(100))
    photo_url = db.Column(db.String(500))
    
    # User stats
    total_reports = db.Column(db.Integer, default=0)
    approved_reports = db.Column(db.Integer, default=0)
    rejected_reports = db.Column(db.Integer, default=0)
    
    # Reputation
    reputation_score = db.Column(db.Float, default=100.0)
    is_banned = db.Column(db.Boolean, default=False)
    ban_reason = db.Column(db.Text)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)
    last_login = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)
    
    # Relationship
    reports = db.relationship('Report', backref='reporter', lazy='dynamic', 
                             foreign_keys='Report.user_id')
    
    def to_dict(self):
        """Convert user to dictionary"""
        return {
            'id': self.id,
            'firebaseUid': self.firebase_uid,
            'email': self.email,
            'displayName': self.display_name,
            'photoUrl': self.photo_url,
            'stats': {
                'totalReports': self.total_reports,
                'approvedReports': self.approved_reports,
                'rejectedReports': self.rejected_reports,
            },
            'reputationScore': self.reputation_score,
            'isBanned': self.is_banned,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'lastLogin': self.last_login.isoformat() if self.last_login else None
        }
    
    def update_stats(self, approved):
        """Update user statistics after report submission"""
        self.total_reports += 1
        if approved:
            self.approved_reports += 1
            # Increase reputation for approved reports
            self.reputation_score = min(100.0, self.reputation_score + 0.5)
        else:
            self.rejected_reports += 1
            # Decrease reputation for rejected reports
            self.reputation_score = max(0.0, self.reputation_score - 2.0)
        
        # Auto-ban if reputation drops too low
        if self.reputation_score < 20.0 and not self.is_banned:
            self.is_banned = True
            self.ban_reason = "Automatic ban due to low reputation score (multiple rejected reports)"
    
    def __repr__(self):
        return f'<User {self.email}>'
