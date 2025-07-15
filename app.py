import os
import asyncio
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_migrate import Migrate
from werkzeug.utils import secure_filename
from config import config
from models import db, TelegramAccount, TelegramGroup, MessageTemplate, Campaign, SentMessage, ScrapedUser, ScheduledTask, AutoReplyRule
from services import telegram_service
from datetime import datetime, timezone
import json

def create_app(config_name=None):
    app = Flask(__name__)
    
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'default')
    
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    # Initialize extensions
    db.init_app(app)
    migrate = Migrate(app, db)
    
    # Create upload directory
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs('sessions', exist_ok=True)
    
    # Routes
    @app.route('/')
    def index():
        # Dashboard data
        total_accounts = TelegramAccount.query.count()
        active_accounts = TelegramAccount.query.filter_by(status='active').count()
        total_groups = TelegramGroup.query.count()
        total_campaigns = Campaign.query.count()
        
        recent_campaigns = Campaign.query.order_by(Campaign.created_at.desc()).limit(5).all()
        
        return render_template('index.html', 
                             total_accounts=total_accounts,
                             active_accounts=active_accounts,
                             total_groups=total_groups,
                             total_campaigns=total_campaigns,
                             recent_campaigns=recent_campaigns)
    
    @app.route('/accounts')
    def accounts():
        accounts = TelegramAccount.query.all()
        return render_template('accounts.html', accounts=accounts)
    
    @app.route('/accounts/add', methods=['GET', 'POST'])
    def add_account():
        if request.method == 'POST':
            data = request.get_json() if request.is_json else request.form
            
            account = TelegramAccount(
                phone_number=data['phone_number'],
                session_name=data['phone_number'].replace('+', ''),
                api_id=data['api_id'],
                api_hash=data['api_hash'],
                nickname=data.get('nickname', '')
            )
            
            try:
                db.session.add(account)
                db.session.commit()
                
                # Try to connect the account
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                success = loop.run_until_complete(
                    telegram_service.create_client(
                        account.id, 
                        account.api_id, 
                        account.api_hash, 
                        account.phone_number
                    )
                )
                loop.close()
                
                if request.is_json:
                    return jsonify({'success': True, 'message': 'Account added successfully'})
                else:
                    flash('Account added successfully', 'success')
                    return redirect(url_for('accounts'))
                    
            except Exception as e:
                db.session.rollback()
                if request.is_json:
                    return jsonify({'success': False, 'message': str(e)})
                else:
                    flash(f'Error adding account: {str(e)}', 'error')
        
        return render_template('add_account.html')
    
    @app.route('/groups')
    def groups():
        groups = TelegramGroup.query.all()
        return render_template('groups.html', groups=groups)
    
    @app.route('/groups/sync/<int:account_id>')
    def sync_groups(account_id):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            dialogs = loop.run_until_complete(telegram_service.get_dialogs(account_id))
            loop.close()
            
            synced_count = 0
            for dialog in dialogs:
                existing_group = TelegramGroup.query.filter_by(group_id=dialog['id']).first()
                if not existing_group:
                    group = TelegramGroup(
                        group_id=dialog['id'],
                        username=dialog['username'],
                        title=dialog['title'],
                        type=dialog['type'],
                        member_count=dialog['participants_count']
                    )
                    db.session.add(group)
                    synced_count += 1
            
            db.session.commit()
            return jsonify({'success': True, 'message': f'Synced {synced_count} groups'})
            
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)})
    
    @app.route('/templates')
    def templates():
        templates = MessageTemplate.query.filter_by(is_active=True).all()
        return render_template('templates.html', templates=templates)
    
    @app.route('/templates/add', methods=['GET', 'POST'])
    def add_template():
        if request.method == 'POST':
            template = MessageTemplate(
                name=request.form['name'],
                content=request.form['content']
            )
            
            # Handle file upload
            if 'media_file' in request.files:
                file = request.files['media_file']
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    template.media_path = file_path
                    template.media_type = filename.split('.')[-1].lower()
            
            db.session.add(template)
            db.session.commit()
            
            flash('Template added successfully', 'success')
            return redirect(url_for('templates'))
        
        return render_template('add_template.html')
    
    @app.route('/campaigns')
    def campaigns():
        campaigns = Campaign.query.order_by(Campaign.created_at.desc()).all()
        return render_template('campaigns.html', campaigns=campaigns)
    
    @app.route('/campaigns/add', methods=['GET', 'POST'])
    def add_campaign():
        if request.method == 'POST':
            data = request.get_json() if request.is_json else request.form
            
            campaign = Campaign(
                name=data['name'],
                template_id=int(data['template_id']),
                interval_seconds=int(data.get('interval_seconds', 0))
            )
            
            # Set target groups and accounts
            if 'target_groups' in data:
                campaign.set_target_groups(data['target_groups'])
            if 'target_accounts' in data:
                campaign.set_target_accounts(data['target_accounts'])
            
            # Set scheduled time if provided
            if 'scheduled_time' in data and data['scheduled_time']:
                campaign.scheduled_time = datetime.fromisoformat(data['scheduled_time'])
                campaign.status = 'scheduled'
            
            db.session.add(campaign)
            db.session.commit()
            
            if request.is_json:
                return jsonify({'success': True, 'campaign_id': campaign.id})
            else:
                flash('Campaign created successfully', 'success')
                return redirect(url_for('campaigns'))
        
        templates = MessageTemplate.query.filter_by(is_active=True).all()
        accounts = TelegramAccount.query.filter_by(status='active').all()
        groups = TelegramGroup.query.filter_by(is_active=True).all()
        
        return render_template('add_campaign.html', 
                             templates=templates, 
                             accounts=accounts, 
                             groups=groups)
    
    @app.route('/campaigns/start/<int:campaign_id>')
    def start_campaign(campaign_id):
        try:
            campaign = Campaign.query.get_or_404(campaign_id)
            template = MessageTemplate.query.get(campaign.template_id)
            
            if not template:
                return jsonify({'success': False, 'message': 'Template not found'})
            
            # Start the campaign
            campaign.status = 'running'
            campaign.started_at = datetime.now(timezone.utc)
            db.session.commit()
            
            # Send messages
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            results = loop.run_until_complete(
                telegram_service.bulk_send_messages(
                    campaign_id=campaign.id,
                    account_ids=campaign.get_target_accounts(),
                    group_ids=campaign.get_target_groups(),
                    message=template.content,
                    media_path=template.media_path,
                    interval=campaign.interval_seconds
                )
            )
            loop.close()
            
            # Update campaign status
            campaign.status = 'completed'
            campaign.completed_at = datetime.now(timezone.utc)
            db.session.commit()
            
            return jsonify({'success': True, 'results': results})
            
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)})
    
    @app.route('/scraper')
    def scraper():
        scraped_users = ScrapedUser.query.order_by(ScrapedUser.scraped_at.desc()).limit(100).all()
        groups = TelegramGroup.query.filter_by(is_active=True).all()
        accounts = TelegramAccount.query.filter_by(status='active').all()
        
        return render_template('scraper.html', 
                             scraped_users=scraped_users,
                             groups=groups,
                             accounts=accounts)
    
    @app.route('/scraper/scrape', methods=['POST'])
    def scrape_users():
        try:
            data = request.get_json()
            account_id = int(data['account_id'])
            group_id = int(data['group_id'])
            limit = int(data.get('limit', 1000))
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            success, message = loop.run_until_complete(
                telegram_service.scrape_group_members(account_id, group_id, limit)
            )
            loop.close()
            
            return jsonify({'success': success, 'message': message})
            
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)})
    
    @app.route('/automation')
    def automation():
        auto_reply_rules = AutoReplyRule.query.filter_by(is_active=True).all()
        return render_template('automation.html', auto_reply_rules=auto_reply_rules)
    
    @app.route('/automation/add_rule', methods=['POST'])
    def add_auto_reply_rule():
        try:
            data = request.get_json()
            
            rule = AutoReplyRule(
                name=data['name'],
                reply_message=data['reply_message']
            )
            
            if 'trigger_keywords' in data:
                rule.set_trigger_keywords(data['trigger_keywords'])
            if 'target_groups' in data:
                rule.set_target_groups(data['target_groups'])
            
            db.session.add(rule)
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'Auto-reply rule added'})
            
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)})
    
    @app.route('/analytics')
    def analytics():
        # Get campaign statistics
        total_sent = SentMessage.query.filter_by(status='sent').count()
        total_failed = SentMessage.query.filter_by(status='failed').count()
        
        # Recent activity
        recent_messages = SentMessage.query.order_by(SentMessage.sent_at.desc()).limit(10).all()
        
        return render_template('analytics.html',
                             total_sent=total_sent,
                             total_failed=total_failed,
                             recent_messages=recent_messages)
    
    # API endpoints
    @app.route('/api/accounts')
    def api_accounts():
        accounts = TelegramAccount.query.all()
        return jsonify([{
            'id': acc.id,
            'phone_number': acc.phone_number,
            'nickname': acc.nickname,
            'status': acc.status,
            'last_active': acc.last_active.isoformat() if acc.last_active else None
        } for acc in accounts])
    
    @app.route('/api/groups')
    def api_groups():
        groups = TelegramGroup.query.all()
        return jsonify([{
            'id': grp.id,
            'group_id': grp.group_id,
            'title': grp.title,
            'username': grp.username,
            'type': grp.type,
            'member_count': grp.member_count
        } for grp in groups])
    
    return app

def init_db():
    """Initialize the database"""
    app = create_app()
    with app.app_context():
        db.create_all()
        print("Database tables created successfully!")

if __name__ == '__main__':
    app = create_app()
    
    # Create tables if they don't exist
    with app.app_context():
        db.create_all()
    
    app.run(
        host=app.config['HOST'],
        port=app.config['PORT'],
        debug=app.config['DEBUG']
    )