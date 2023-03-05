# Generated by Django 4.1.7 on 2023-03-04 14:35

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("Benches", "0002_benches_thumbnail"),
    ]

    operations = [
        migrations.AlterField(
            model_name="benches",
            name="qr_code",
            field=models.ImageField(
                blank=True, null=True, upload_to="images/qr_codes/"
            ),
        ),
        migrations.AlterField(
            model_name="benches",
            name="thumbnail",
            field=models.ImageField(
                blank=True, null=True, upload_to="images/bench_thumbnails/"
            ),
        ),
        migrations.CreateModel(
            name="Audio",
            fields=[
                ("audio_id", models.AutoField(primary_key=True, serialize=False)),
                ("audio_binary", models.BooleanField(default=False)),
                (
                    "audio_file",
                    models.FileField(blank=True, null=True, upload_to="audio_files/"),
                ),
                (
                    "length_category",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("0-5", "0-5 minutes"),
                            ("5-10", "5-10 minutes"),
                            (">10", "greater than 10 minutes"),
                        ],
                        max_length=30,
                        null=True,
                    ),
                ),
                (
                    "contributor",
                    models.CharField(blank=True, max_length=100, null=True),
                ),
                (
                    "bench_id",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="audios",
                        to="Benches.benches",
                    ),
                ),
            ],
        ),
    ]
