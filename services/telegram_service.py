import asyncio
import os
from telethon import TelegramClient, events
from telethon.tl.functions.messages import GetDialogsRequest
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.contacts import SearchRequest
from telethon.tl.types import InputPeerEmpty, PeerUser, PeerChat, PeerChannel, InputMessagesFilterEmpty
from telethon.errors import SessionPasswordNeededError, FloodWaitError
from models import db, TelegramAccount, TelegramGroup, SentMessage, ScrapedUser
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

class TelegramService:
    def __init__(self):
        self.clients = {}
        self.active_sessions = {}
    
    async def create_client(self, account_id, api_id, api_hash, phone_number):
        """Create a new Telegram client for an account"""
        try:
            session_name = f"sessions/{phone_number}"
            os.makedirs("sessions", exist_ok=True)
            
            client = TelegramClient(session_name, api_id, api_hash)
            await client.start(phone=phone_number)
            
            if await client.is_user_authorized():
                self.clients[account_id] = client
                
                # Update account status
                account = TelegramAccount.query.get(account_id)
                if account:
                    account.status = 'active'
                    account.last_active = datetime.now(timezone.utc)
                    account.is_verified = True
                    db.session.commit()
                
                return True
            else:
                logger.warning(f"Account {phone_number} not authorized")
                return False
                
        except SessionPasswordNeededError:
            logger.error(f"2FA enabled for {phone_number}")
            return False
        except Exception as e:
            logger.error(f"Error creating client for {phone_number}: {str(e)}")
            return False
    
    async def get_client(self, account_id):
        """Get existing client or create new one"""
        if account_id in self.clients:
            return self.clients[account_id]
        
        account = TelegramAccount.query.get(account_id)
        if not account:
            return None
        
        success = await self.create_client(
            account_id, 
            account.api_id, 
            account.api_hash, 
            account.phone_number
        )
        
        return self.clients.get(account_id) if success else None
    
    async def send_message(self, account_id, group_id, message, media_path=None):
        """Send a message to a group"""
        try:
            client = await self.get_client(account_id)
            if not client:
                return False, "Client not available"
            
            group = TelegramGroup.query.filter_by(group_id=group_id).first()
            if not group:
                return False, "Group not found"
            
            # Send message
            if media_path and os.path.exists(media_path):
                sent_message = await client.send_file(
                    group_id, 
                    media_path, 
                    caption=message
                )
            else:
                sent_message = await client.send_message(group_id, message)
            
            return True, sent_message.id
            
        except FloodWaitError as e:
            error_msg = f"Flood wait: {e.seconds} seconds"
            logger.warning(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Error sending message: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    async def bulk_send_messages(self, campaign_id, account_ids, group_ids, message, media_path=None, interval=0):
        """Send messages to multiple groups using multiple accounts"""
        results = []
        
        for account_id in account_ids:
            for group_id in group_ids:
                success, result = await self.send_message(account_id, group_id, message, media_path)
                
                # Log the result
                sent_msg = SentMessage(
                    campaign_id=campaign_id,
                    account_id=account_id,
                    group_id=TelegramGroup.query.filter_by(group_id=group_id).first().id,
                    message_id=result if success else None,
                    status='sent' if success else 'failed',
                    sent_at=datetime.now(timezone.utc) if success else None,
                    error_message=result if not success else None
                )
                db.session.add(sent_msg)
                
                results.append({
                    'account_id': account_id,
                    'group_id': group_id,
                    'success': success,
                    'result': result
                })
                
                # Wait between messages if interval is set
                if interval > 0:
                    await asyncio.sleep(interval)
        
        db.session.commit()
        return results
    
    async def join_group(self, account_id, group_link):
        """Join a group or channel"""
        try:
            client = await self.get_client(account_id)
            if not client:
                return False, "Client not available"
            
            # Join the group
            result = await client(JoinChannelRequest(group_link))
            
            # Get group info
            entity = await client.get_entity(group_link)
            
            # Save group info
            group = TelegramGroup(
                group_id=entity.id,
                username=entity.username,
                title=entity.title,
                type='channel' if hasattr(entity, 'broadcast') and entity.broadcast else 'supergroup',
                member_count=getattr(entity, 'participants_count', 0)
            )
            
            existing_group = TelegramGroup.query.filter_by(group_id=entity.id).first()
            if not existing_group:
                db.session.add(group)
                db.session.commit()
            
            return True, "Successfully joined group"
            
        except Exception as e:
            error_msg = f"Error joining group: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    async def scrape_group_members(self, account_id, group_id, limit=1000):
        """Scrape members from a group"""
        try:
            client = await self.get_client(account_id)
            if not client:
                return False, "Client not available"
            
            # Get group entity
            entity = await client.get_entity(group_id)
            
            # Get participants
            participants = await client.get_participants(entity, limit=limit)
            
            scraped_count = 0
            group_record = TelegramGroup.query.filter_by(group_id=group_id).first()
            
            for user in participants:
                if user.bot:
                    continue
                
                # Check if user already exists
                existing_user = ScrapedUser.query.filter_by(
                    user_id=user.id,
                    source_group_id=group_record.id
                ).first()
                
                if not existing_user:
                    scraped_user = ScrapedUser(
                        user_id=user.id,
                        username=user.username,
                        first_name=user.first_name,
                        last_name=user.last_name,
                        phone=getattr(user, 'phone', None),
                        is_bot=user.bot,
                        is_verified=getattr(user, 'verified', False),
                        is_premium=getattr(user, 'premium', False),
                        source_group_id=group_record.id,
                        source_account_id=account_id
                    )
                    db.session.add(scraped_user)
                    scraped_count += 1
            
            db.session.commit()
            return True, f"Scraped {scraped_count} users"
            
        except Exception as e:
            error_msg = f"Error scraping members: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    async def get_dialogs(self, account_id):
        """Get all dialogs (groups, channels, private chats) for an account"""
        try:
            client = await self.get_client(account_id)
            if not client:
                return []
            
            dialogs = await client.get_dialogs()
            result = []
            
            for dialog in dialogs:
                if hasattr(dialog.entity, 'id'):
                    result.append({
                        'id': dialog.entity.id,
                        'title': getattr(dialog.entity, 'title', dialog.name),
                        'username': getattr(dialog.entity, 'username', None),
                        'type': 'channel' if hasattr(dialog.entity, 'broadcast') else 'group',
                        'participants_count': getattr(dialog.entity, 'participants_count', 0)
                    })
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting dialogs: {str(e)}")
            return []
    
    async def search_and_join_groups(self, account_id, keywords, limit=10):
        """Search for groups by keywords and join them"""
        try:
            client = await self.get_client(account_id)
            if not client:
                return False, "Client not available"
            
            joined_groups = []
            
            for keyword in keywords:
                # Search for groups
                results = await client(SearchRequest(
                    peer=InputPeerEmpty(),
                    q=keyword,
                    filter=InputMessagesFilterEmpty(),
                    min_date=None,
                    max_date=None,
                    offset_id=0,
                    add_offset=0,
                    limit=limit,
                    max_id=0,
                    min_id=0,
                    hash=0
                ))
                
                for chat in results.chats:
                    if hasattr(chat, 'username') and chat.username:
                        success, msg = await self.join_group(account_id, chat.username)
                        if success:
                            joined_groups.append(chat.title)
            
            return True, f"Joined {len(joined_groups)} groups"
            
        except Exception as e:
            error_msg = f"Error searching and joining groups: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def disconnect_all(self):
        """Disconnect all clients"""
        for client in self.clients.values():
            try:
                asyncio.create_task(client.disconnect())
            except:
                pass
        self.clients.clear()

# Global service instance
telegram_service = TelegramService()