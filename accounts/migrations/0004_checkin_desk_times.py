from django.db import migrations, models


def keep_existing_arrivals_inside(apps, schema_editor):
    CheckIn = apps.get_model("accounts", "CheckIn")
    for row in CheckIn.objects.all():
        row.status = "approved"
        row.approved_at = row.checked_in_at
        row.save(update_fields=["status", "approved_at"])


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_checkin"),
    ]

    operations = [
        migrations.AddField(
            model_name="checkin",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("approved", "Inside"),
                    ("checked_out", "Checked out"),
                ],
                default="approved",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="checkin",
            name="approved_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="checkin",
            name="checked_out_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(keep_existing_arrivals_inside, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="checkin",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("approved", "Inside"),
                    ("checked_out", "Checked out"),
                ],
                default="pending",
                max_length=16,
            ),
        ),
    ]
