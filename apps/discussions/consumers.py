"""
discussions/consumers.py — WebSocket consumer for real-time discussion threads.

Clients connect to:
    ws://<host>/ws/discussions/<thread_id>/

Authentication:
    Pass JWT token as a query param: ?token=<access_token>

Events sent to client:
    - new_post: A new post was added to the thread
    - post_edited: A post was edited
    - post_deleted: A post was deleted
    - thread_locked: The thread was locked
    - user_typing: Another user is typing

Events received from client:
    - new_post: { "content": "..." }
    - edit_post: { "post_id": "...", "content": "..." }
    - delete_post: { "post_id": "..." }
    - typing: {}
"""
import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError

from .models import Thread, Post

logger = logging.getLogger(__name__)

# In-memory presence tracking: { thread_id: { user_email: { name, channel_name } } }
# This tracks which users are currently connected to each thread room.
_active_users = {}


class DiscussionConsumer(AsyncJsonWebsocketConsumer):
    """Real-time WebSocket consumer for a single discussion thread."""

    async def connect(self):
        self.thread_id = self.scope['url_route']['kwargs']['thread_id']
        self.room_group_name = f'discussion_{self.thread_id}'

        # Authenticate via JWT token in query string
        self.user = await self._authenticate()
        if self.user is None:
            await self.close(code=4001)
            return

        # Verify thread exists
        self.thread = await self._get_thread()
        if self.thread is None:
            await self.close(code=4004)
            return

        # Join the thread group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name,
        )
        await self.accept()

        # Track active user presence
        user_name = await self._get_author_name(self.user)
        if self.thread_id not in _active_users:
            _active_users[self.thread_id] = {}
        _active_users[self.thread_id][self.user.email] = {
            'name': user_name,
            'channel_name': self.channel_name,
        }

        # Send a welcome message with connection info + current active users
        await self.send_json({
            'type': 'connection_established',
            'thread_id': self.thread_id,
            'user': self.user.email,
            'active_users': self._get_active_users_list(),
        })

        # Broadcast updated presence to all others in the thread
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'discussion.presence_update',
                'active_users': self._get_active_users_list(),
                'event': 'joined',
                'user_email': self.user.email,
                'user_name': user_name,
            },
        )

    async def disconnect(self, close_code):
        # Remove from presence tracking
        if hasattr(self, 'thread_id') and hasattr(self, 'user') and self.user:
            thread_users = _active_users.get(self.thread_id, {})
            # Only remove if this is the same channel (user might have multiple tabs)
            if thread_users.get(self.user.email, {}).get('channel_name') == self.channel_name:
                thread_users.pop(self.user.email, None)
            if not thread_users:
                _active_users.pop(self.thread_id, None)

            # Broadcast updated presence
            if hasattr(self, 'room_group_name'):
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'discussion.presence_update',
                        'active_users': self._get_active_users_list(),
                        'event': 'left',
                        'user_email': self.user.email,
                        'user_name': await self._get_author_name(self.user),
                    },
                )

        # Leave the thread group
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name,
            )

    async def receive_json(self, content):
        """Handle incoming messages from the client."""
        action = content.get('action')

        if action == 'new_post':
            await self._handle_new_post(content)
        elif action == 'edit_post':
            await self._handle_edit_post(content)
        elif action == 'delete_post':
            await self._handle_delete_post(content)
        elif action == 'typing':
            await self._handle_typing()
        else:
            await self.send_json({'type': 'error', 'message': f'Unknown action: {action}'})

    # ─── Action handlers ────────────────────────────────────────────────

    async def _handle_new_post(self, content):
        """Create a new post and broadcast to the group."""
        text = (content.get('content') or '').strip()
        if not text:
            await self.send_json({'type': 'error', 'message': 'Content is required.'})
            return

        # Check if thread is locked
        thread = await self._get_thread()
        if thread and thread.is_locked and not self.user.is_staff:
            await self.send_json({'type': 'error', 'message': 'This thread is locked.'})
            return

        post = await self._create_post(text)
        if post is None:
            await self.send_json({'type': 'error', 'message': 'Failed to create post.'})
            return

        # Broadcast to group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'discussion.new_post',
                'post': {
                    'id': str(post.id),
                    'thread': str(post.thread_id),
                    'author': str(post.author_id),
                    'author_name': await self._get_author_name(post.author),
                    'author_email': post.author.email,
                    'content': post.content,
                    'is_edited': post.is_edited,
                    'created_at': post.created_at.isoformat(),
                    'updated_at': post.updated_at.isoformat(),
                },
            },
        )

    async def _handle_edit_post(self, content):
        """Edit an existing post and broadcast the update."""
        post_id = content.get('post_id')
        text = (content.get('content') or '').strip()
        if not post_id or not text:
            await self.send_json({'type': 'error', 'message': 'post_id and content are required.'})
            return

        post = await self._update_post(post_id, text)
        if post is None:
            return  # Error already sent

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'discussion.post_edited',
                'post': {
                    'id': str(post.id),
                    'thread': str(post.thread_id),
                    'author': str(post.author_id),
                    'author_name': await self._get_author_name(post.author),
                    'author_email': post.author.email,
                    'content': post.content,
                    'is_edited': post.is_edited,
                    'created_at': post.created_at.isoformat(),
                    'updated_at': post.updated_at.isoformat(),
                },
            },
        )

    async def _handle_delete_post(self, content):
        """Delete a post and broadcast the removal."""
        post_id = content.get('post_id')
        if not post_id:
            await self.send_json({'type': 'error', 'message': 'post_id is required.'})
            return

        success = await self._delete_post(post_id)
        if not success:
            return  # Error already sent

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'discussion.post_deleted',
                'post_id': post_id,
            },
        )

    async def _handle_typing(self):
        """Broadcast typing indicator to other users in the thread."""
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'discussion.user_typing',
                'user_email': self.user.email,
                'user_name': await self._get_author_name(self.user),
            },
        )

    # ─── Group message handlers (broadcast to all clients) ──────────────

    async def discussion_new_post(self, event):
        """Send new post event to WebSocket client."""
        await self.send_json({
            'type': 'new_post',
            'post': event['post'],
        })

    async def discussion_post_edited(self, event):
        """Send post edited event to WebSocket client."""
        await self.send_json({
            'type': 'post_edited',
            'post': event['post'],
        })

    async def discussion_post_deleted(self, event):
        """Send post deleted event to WebSocket client."""
        await self.send_json({
            'type': 'post_deleted',
            'post_id': event['post_id'],
        })

    async def discussion_user_typing(self, event):
        """Send typing indicator — skip sending to the user who is typing."""
        if event.get('user_email') != self.user.email:
            await self.send_json({
                'type': 'user_typing',
                'user_email': event['user_email'],
                'user_name': event['user_name'],
            })

    async def discussion_thread_locked(self, event):
        """Notify all clients that the thread has been locked."""
        await self.send_json({
            'type': 'thread_locked',
            'thread_id': event['thread_id'],
        })

    async def discussion_presence_update(self, event):
        """Send active users list to all clients in the thread."""
        await self.send_json({
            'type': 'presence_update',
            'active_users': event['active_users'],
            'event': event.get('event'),  # 'joined' or 'left'
            'user_email': event.get('user_email'),
            'user_name': event.get('user_name'),
        })

    # ─── Presence helpers ───────────────────────────────────────────────

    def _get_active_users_list(self):
        """Return a list of active users for the current thread."""
        thread_users = _active_users.get(self.thread_id, {})
        return [
            {'email': email, 'name': info['name']}
            for email, info in thread_users.items()
        ]

    # ─── Authentication ─────────────────────────────────────────────────

    async def _authenticate(self):
        """Authenticate user from JWT token in query string."""
        query_string = self.scope.get('query_string', b'').decode()
        params = dict(p.split('=', 1) for p in query_string.split('&') if '=' in p)
        token_str = params.get('token')

        if not token_str:
            return None

        try:
            token = AccessToken(token_str)
            user_id = token.get('user_id')
            user = await self._get_user(user_id)
            return user
        except TokenError:
            return None

    @database_sync_to_async
    def _get_user(self, user_id):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None

    # ─── Database helpers ───────────────────────────────────────────────

    @database_sync_to_async
    def _get_thread(self):
        try:
            return Thread.objects.get(id=self.thread_id)
        except Thread.DoesNotExist:
            return None

    @database_sync_to_async
    def _create_post(self, content):
        try:
            return Post.objects.create(
                thread_id=self.thread_id,
                author=self.user,
                content=content,
            )
        except Exception as e:
            logger.error(f'Failed to create post: {e}')
            return None

    @database_sync_to_async
    def _update_post(self, post_id, content):
        try:
            post = Post.objects.select_related('author').get(id=post_id, thread_id=self.thread_id)
        except Post.DoesNotExist:
            return None

        if post.author != self.user and not self.user.is_staff:
            return None

        post.content = content
        post.save()
        return post

    @database_sync_to_async
    def _delete_post(self, post_id):
        try:
            post = Post.objects.select_related('author', 'thread').get(
                id=post_id, thread_id=self.thread_id
            )
        except Post.DoesNotExist:
            return False

        is_reply_author = post.author == self.user
        is_thread_author = post.thread.author == self.user
        if not (is_reply_author or is_thread_author or self.user.is_staff):
            return False

        post.delete()
        return True

    @database_sync_to_async
    def _get_author_name(self, user):
        return getattr(user, 'full_name', None) or user.email
