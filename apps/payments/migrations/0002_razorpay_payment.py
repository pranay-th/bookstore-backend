"""
Rework the Payment model for Razorpay.

Replaces the Phase-0 placeholder fields (method, gateway_ref, USD default,
pending/completed/failed/refunded statuses) with Razorpay-specific fields:
razorpay_order_id (unique), razorpay_payment_id, razorpay_signature, an
error_description, an INR currency default and created/paid/failed statuses.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0001_initial'),
    ]

    operations = [
        # Drop placeholder fields no longer used.
        migrations.RemoveField(model_name='payment', name='method'),
        migrations.RemoveField(model_name='payment', name='gateway_ref'),

        # New Razorpay identifier fields.
        migrations.AddField(
            model_name='payment',
            name='razorpay_order_id',
            field=models.CharField(default='', db_index=True, max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='payment',
            name='razorpay_payment_id',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='payment',
            name='razorpay_signature',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='payment',
            name='error_description',
            field=models.TextField(blank=True, default=''),
        ),

        # Adjust existing fields.
        migrations.AlterField(
            model_name='payment',
            name='currency',
            field=models.CharField(default='INR', max_length=3),
        ),
        migrations.AlterField(
            model_name='payment',
            name='status',
            field=models.CharField(
                choices=[('created', 'Created'), ('paid', 'Paid'), ('failed', 'Failed')],
                default='created',
                max_length=20,
            ),
        ),

        # Unique constraint on the Razorpay order id (guards against dup processing).
        migrations.AlterField(
            model_name='payment',
            name='razorpay_order_id',
            field=models.CharField(db_index=True, max_length=255, unique=True),
        ),

        # Model-level ordering.
        migrations.AlterModelOptions(
            name='payment',
            options={'ordering': ['-created_at']},
        ),
    ]
