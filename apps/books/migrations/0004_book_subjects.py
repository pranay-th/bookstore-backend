from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("books", "0003_book_owner"),
    ]

    operations = [
        migrations.AddField(
            model_name="book",
            name="subjects",
            field=models.TextField(blank=True, default=""),
        ),
    ]
