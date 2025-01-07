# Generated by Django 5.1.4 on 2025-01-07 20:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('airport_info', '0005_datasource_alter_airfield_ident_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='airfield',
            name='type',
            field=models.CharField(choices=[('balloonport', 'Balloon Port'), ('closed', 'Closed'), ('heliport', 'Heliport'), ('large_airport', 'Large Airport'), ('medium_airport', 'Medium Airport'), ('seaplane_base', 'Seaplane Base'), ('small_airport', 'Small Airport')], default='small_airport', max_length=20),
        ),
    ]
