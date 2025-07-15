from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
import json

db = SQLAlchemy()

class TelegramAccount(db.Model):
    __tablename__ = 'telegram_accounts'
    
    id = db.Column(db.Integer, primary_key=True)
    phone_number = db.Column(db.String(20), unique=True, nullable=False)
    session_name = db.Column(db.String(100), unique=True, nullable=False)
    api_id = db.Column(db.String(20), nullable=False)
    api_hash = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default='inactive')  # active, inactive, banned, limited
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_active = db.Column(db.DateTime)
    is_verified = db.Column(db.Boolean, default=False)
    nickname = db.Column(db.String(100))
    
    # Relationships
    sent_messages = db.relationship('SentMessage', backref='account', lazy=True)
    scraped_users = db.relationship('ScrapedUser', backref='source_account', lazy=True)

class TelegramGroup(db.Model):
    __tablename__ = 'telegram_groups'
    
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.BigInteger, unique=True, nullable=False)
    username = db.Column(db.String(100), unique=True)
    title = db.Column(db.String(200), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # group, supergroup, channel
    member_count = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    join_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    description = db.Column(db.Text)
    invite_link = db.Column(db.String(200))
    
    # Relationships
    sent_messages = db.relationship('SentMessage', backref='group', lazy=True)
    scraped_users = db.relationship('ScrapedUser', backref='source_group', lazy=True)

class MessageTemplate(db.Model):
    __tablename__ = 'message_templates'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    media_path = db.Column(db.String(200))
    media_type = db.Column(db.String(20))  # image, video, document
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    campaigns = db.relationship('Campaign', backref='template', lazy=True)

class Campaign(db.Model):
    __tablename__ = 'campaigns'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    template_id = db.Column(db.Integer, db.ForeignKey('message_templates.id'), nullable=False)
    status = db.Column(db.String(20), default='draft')  # draft, scheduled, running, completed, paused
    target_groups = db.Column(db.Text)  # JSON array of group IDs
    target_accounts = db.Column(db.Text)  # JSON array of account IDs
    scheduled_time = db.Column(db.DateTime)
    interval_seconds = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    
    # Relationships
    sent_messages = db.relationship('SentMessage', backref='campaign', lazy=True)
    
    def get_target_groups(self):
        return json.loads(self.target_groups) if self.target_groups else []
    
    def set_target_groups(self, groups):
        self.target_groups = json.dumps(groups)
    
    def get_target_accounts(self):
        return json.loads(self.target_accounts) if self.target_accounts else []
    
    def set_target_accounts(self, accounts):
        self.target_accounts = json.dumps(accounts)

class SentMessage(db.Model):
    __tablename__ = 'sent_messages'
    
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id'), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('telegram_accounts.id'), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('telegram_groups.id'), nullable=False)
    message_id = db.Column(db.BigInteger)
    status = db.Column(db.String(20), default='pending')  # pending, sent, failed, delivered
    sent_at = db.Column(db.DateTime)
    error_message = db.Column(db.Text)
    views = db.Column(db.Integer, default=0)
    forwards = db.Column(db.Integer, default=0)
    replies = db.Column(db.Integer, default=0)

class ScrapedUser(db.Model):
    __tablename__ = 'scraped_users'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.BigInteger, nullable=False)
    username = db.Column(db.String(100))
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    is_bot = db.Column(db.Boolean, default=False)
    is_verified = db.Column(db.Boolean, default=False)
    is_premium = db.Column(db.Boolean, default=False)
    last_seen = db.Column(db.DateTime)
    source_group_id = db.Column(db.Integer, db.ForeignKey('telegram_groups.id'), nullable=False)
    source_account_id = db.Column(db.Integer, db.ForeignKey('telegram_accounts.id'), nullable=False)
    scraped_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    is_active = db.Column(db.Boolean, default=True)

class ScheduledTask(db.Model):
    __tablename__ = 'scheduled_tasks'
    
    id = db.Column(db.Integer, primary_key=True)
    task_type = db.Column(db.String(50), nullable=False)  # send_message, join_group, scrape_users
    task_data = db.Column(db.Text)  # JSON data for the task
    scheduled_time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, running, completed, failed
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    executed_at = db.Column(db.DateTime)
    error_message = db.Column(db.Text)
    
    def get_task_data(self):
        return json.loads(self.task_data) if self.task_data else {}
    
    def set_task_data(self, data):
        self.task_data = json.dumps(data)

class AutoReplyRule(db.Model):
    __tablename__ = 'auto_reply_rules'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    trigger_keywords = db.Column(db.Text)  # JSON array of keywords
    reply_message = db.Column(db.Text, nullable=False)
    target_groups = db.Column(db.Text)  # JSON array of group IDs
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    def get_trigger_keywords(self):
        return json.loads(self.trigger_keywords) if self.trigger_keywords else []
    
    def set_trigger_keywords(self, keywords):
        self.trigger_keywords = json.dumps(keywords)
    
    def get_target_groups(self):
        return json.loads(self.target_groups) if self.target_groups else []
    
    def set_target_groups(self, groups):
        self.target_groups = json.dumps(groups)