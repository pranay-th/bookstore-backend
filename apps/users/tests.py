"""
users/tests.py — Phase 0 placeholder tests.
TODO: Add full test coverage for User CRUD, UserProfile, and UserAddress.
"""
from django.test import TestCase
from .models import User, UserProfile, UserAddress


class UserModelTestCase(TestCase):
    """Tests for the User model."""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='placeholder123',
            first_name='Test',
            last_name='User',
        )

    def test_user_created_with_uuid_pk(self):
        """User PK should be a UUID."""
        import uuid
        self.assertIsInstance(self.user.id, uuid.UUID)

    def test_user_str(self):
        self.assertEqual(str(self.user), 'test@example.com')

    def test_full_name(self):
        self.assertEqual(self.user.full_name, 'Test User')

    # TODO: test_user_profile_creation
    # TODO: test_user_address_creation
    # TODO: test_default_address_constraint
