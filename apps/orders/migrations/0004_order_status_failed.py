"""
Add a 'failed' choice to Order.status.

Choices are enforced at the application layer, not the DB, so this AlterField
only updates Django's state — it does not alter the column. Safe and instant.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0003_order_coupon_discount'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(
                choices=[
                    ('pending', 'Pending'),
                    ('confirmed', 'Confirmed'),
                    ('failed', 'Failed'),
                    ('processing', 'Processing'),
                    ('shipped', 'Shipped'),
                    ('delivered', 'Delivered'),
                    ('cancelled', 'Cancelled'),
                    ('refunded', 'Refunded'),
                ],
                default='pending',
                max_length=20,
            ),
        ),
    ]
