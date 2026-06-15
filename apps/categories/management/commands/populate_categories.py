"""
Management command to seed the categories table.

Usage:
    python manage.py populate_categories
    python manage.py populate_categories --clear
"""
from django.core.management.base import BaseCommand

from apps.categories.models import Category

CATEGORIES = [
    {"name": "Fiction", "icon": "BookOpen", "description": "Novels, short stories & literary works"},
    {"name": "Mystery & Thriller", "icon": "Search", "description": "Crime, suspense & detective stories"},
    {"name": "Science Fiction", "icon": "Rocket", "description": "Futuristic & speculative worlds"},
    {"name": "Fantasy", "icon": "Sparkles", "description": "Magic, myth & epic adventures"},
    {"name": "Romance", "icon": "Heart", "description": "Love stories & relationships"},
    {"name": "History", "icon": "Landmark", "description": "Past events, eras & civilizations"},
    {"name": "Biography", "icon": "UserRound", "description": "Lives of remarkable people"},
    {"name": "Science", "icon": "FlaskConical", "description": "Physics, biology, chemistry & more"},
    {"name": "Technology", "icon": "Cpu", "description": "Computing, engineering & innovation"},
    {"name": "Philosophy", "icon": "Brain", "description": "Ideas, ethics & the human mind"},
    {"name": "Poetry", "icon": "Feather", "description": "Verse, rhyme & lyrical works"},
    {"name": "Children's", "icon": "Baby", "description": "Picture books & young readers"},
    {"name": "Business", "icon": "Briefcase", "description": "Economics, finance & management"},
    {"name": "Art & Design", "icon": "Palette", "description": "Visual arts, architecture & design"},
    {"name": "Cooking", "icon": "ChefHat", "description": "Recipes, cuisine & food culture"},
    {"name": "Travel", "icon": "Plane", "description": "Destinations, guides & adventures"},
]


class Command(BaseCommand):
    help = "Seed the database with default book categories"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear", action="store_true",
            help="Delete all existing categories before seeding",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            deleted, _ = Category.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Deleted {deleted} existing categories."))

        created = 0
        for entry in CATEGORIES:
            obj, was_created = Category.objects.get_or_create(
                name=entry["name"],
                defaults={
                    "icon": entry["icon"],
                    "description": entry["description"],
                    "is_active": True,
                },
            )
            if was_created:
                created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Done! Created {created} new categories. "
                f"Total: {Category.objects.count()}"
            )
        )
