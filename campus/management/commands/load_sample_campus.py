from django.core.management.base import BaseCommand

from campus.models import Building, Office


class Command(BaseCommand):
    help = "Load clearly labelled sample buildings and offices for local testing."

    def handle(self, *args, **options):
        buildings = {
            name: (
                "SAMPLE DATA - replace after the campus directory is confirmed."
            )
            for name in (
                "Sample North Building",
                "Sample South Building",
                "Sample East Building",
            )
        }
        building_objects = {}
        created_buildings = 0
        for name, description in buildings.items():
            building, created = Building.objects.get_or_create(
                name=name,
                defaults={"description": description, "is_active": True},
            )
            building_objects[name] = building
            created_buildings += created

        offices = [
            (
                "Sample Admissions Office",
                "Sample North Building",
                "1F",
                "101",
                "SAMPLE DATA - Enter the main doors and turn left.",
            ),
            (
                "Sample Registrar Office",
                "Sample North Building",
                "2F",
                "201",
                "SAMPLE DATA - Take the stairs to the second floor.",
            ),
            (
                "Sample Student Services Office",
                "Sample South Building",
                "1F",
                "102",
                "SAMPLE DATA - The office is beside the main reception.",
            ),
            (
                "Sample Library Office",
                "Sample East Building",
                "3F",
                "301",
                "SAMPLE DATA - Use the east entrance and take the elevator.",
            ),
        ]
        created_offices = 0
        for name, building_name, floor, room_number, directions in offices:
            _, created = Office.objects.get_or_create(
                building=building_objects[building_name],
                floor=floor,
                room_number=room_number,
                defaults={
                    "name": name,
                    "directions": directions,
                    "is_active": True,
                },
            )
            created_offices += created

        self.stdout.write(
            self.style.SUCCESS(
                "Sample campus data ready: "
                f"{created_buildings} buildings and {created_offices} offices created. "
                "All sample records are labelled SAMPLE DATA."
            )
        )
