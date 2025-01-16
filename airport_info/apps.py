from django.apps import AppConfig
from django.db.models.signals import post_migrate


def import_airports_if_needed(sender, **kwargs):
    from django.core.management import call_command
    from airport_info.models import Airfield
    
    # Check if we have any airports in the database
    if Airfield.objects.count() == 0:
        print("No airports found in database. Importing from CSV...")
        try:
            call_command('import_airports')
            print("Airport import completed successfully")
        except Exception as e:
            print(f"Error importing airports: {str(e)}")


class AirportInfoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'airport_info'

    def ready(self):
        # Connect the post_migrate signal to our import function
        post_migrate.connect(import_airports_if_needed, sender=self)
