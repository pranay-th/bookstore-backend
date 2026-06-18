"""
Rework the Payment model for Razorpay.

This migration is written to be IDEMPOTENT: a previous deploy applied it
partially (columns + a leftover varchar_pattern_ops "_like" index were created)
without recording it in django_migrations, so a naive re-run fails with
"relation ... already exists".

We use SeparateDatabaseAndState:
  - state_operations  : tell Django the final model shape (no DB effect).
  - database_operations: guarded raw SQL (IF EXISTS / IF NOT EXISTS) that can
                          run safely whether or not the earlier attempt ran.
"""
from django.db import migrations, models


IDEMPOTENT_SQL = """
ALTER TABLE payments DROP COLUMN IF EXISTS method;
ALTER TABLE payments DROP COLUMN IF EXISTS gateway_ref;

ALTER TABLE payments ADD COLUMN IF NOT EXISTS razorpay_order_id   varchar(255) NOT NULL DEFAULT '';
ALTER TABLE payments ADD COLUMN IF NOT EXISTS razorpay_payment_id varchar(255) NOT NULL DEFAULT '';
ALTER TABLE payments ADD COLUMN IF NOT EXISTS razorpay_signature  varchar(255) NOT NULL DEFAULT '';
ALTER TABLE payments ADD COLUMN IF NOT EXISTS error_description   text         NOT NULL DEFAULT '';

ALTER TABLE payments ALTER COLUMN currency SET DEFAULT 'INR';
ALTER TABLE payments ALTER COLUMN status   SET DEFAULT 'created';

-- Drop any leftover indexes from the partial run, then (re)create a clean
-- unique index. All guarded so this block is safe to run repeatedly.
DROP INDEX IF EXISTS payments_razorpay_order_id_bff90b31_like;
DROP INDEX IF EXISTS payments_razorpay_order_id_bff90b31;
CREATE UNIQUE INDEX IF NOT EXISTS payments_razorpay_order_id_uniq
    ON payments (razorpay_order_id);
"""

REVERSE_SQL = """
DROP INDEX IF EXISTS payments_razorpay_order_id_uniq;
ALTER TABLE payments DROP COLUMN IF EXISTS razorpay_order_id;
ALTER TABLE payments DROP COLUMN IF EXISTS razorpay_payment_id;
ALTER TABLE payments DROP COLUMN IF EXISTS razorpay_signature;
ALTER TABLE payments DROP COLUMN IF EXISTS error_description;
ALTER TABLE payments ADD COLUMN IF NOT EXISTS method      varchar(20)  NOT NULL DEFAULT 'card';
ALTER TABLE payments ADD COLUMN IF NOT EXISTS gateway_ref varchar(255) NOT NULL DEFAULT '';
ALTER TABLE payments ALTER COLUMN currency SET DEFAULT 'USD';
ALTER TABLE payments ALTER COLUMN status   SET DEFAULT 'pending';
"""


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            # Real DB changes — idempotent, partial-run safe.
            database_operations=[
                migrations.RunSQL(sql=IDEMPOTENT_SQL, reverse_sql=REVERSE_SQL),
            ],
            # Django's view of the model after this migration.
            state_operations=[
                migrations.RemoveField(model_name='payment', name='method'),
                migrations.RemoveField(model_name='payment', name='gateway_ref'),
                migrations.AddField(
                    model_name='payment',
                    name='razorpay_order_id',
                    field=models.CharField(default='', max_length=255, unique=True),
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
                migrations.AlterModelOptions(
                    name='payment',
                    options={'ordering': ['-created_at']},
                ),
            ],
        ),
    ]
