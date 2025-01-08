# Generated by Django 5.1.4 on 2025-01-07 19:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('airport_info', '0004_remove_airfield_airport_inf_iata_id_bb6a46_idx_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='DataSource',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('url', models.URLField(max_length=500)),
                ('last_download', models.DateTimeField(auto_now=True)),
                ('last_etag', models.CharField(blank=True, max_length=100, null=True)),
                ('last_modified', models.CharField(blank=True, max_length=100, null=True)),
            ],
        ),
        migrations.AlterField(
            model_name='airfield',
            name='ident',
            field=models.CharField(default='', max_length=10),
        ),
        migrations.AlterField(
            model_name='airfield',
            name='iso_region',
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
        migrations.AlterField(
            model_name='airfield',
            name='municipality',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='airfield',
            name='type',
            field=models.CharField(choices=[('heliport', 'Heliport'), ('small_airport', 'Small Airport'), ('closed', 'Closed')], default='small_airport', max_length=20),
        ),
    ]