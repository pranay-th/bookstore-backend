from django.db import migrations


class Migration(migrations.Migration):
    """Reverts the `subjects` column added in 0004.

    Net effect with 0004 is no column, keeping migration state consistent with
    the model whether or not 0004 was already applied to a given database.
    """

    dependencies = [
        ("books", "0004_book_subjects"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="book",
            name="subjects",
        ),
    ]
