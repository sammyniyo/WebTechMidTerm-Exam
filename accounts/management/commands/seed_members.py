from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand

from accounts.models import CampusMember, StaffProfile, StudentProfile

STUDENTS = [
    {
        "member": {
            "campus_id": "20251MBI049",
            "internal_id": 101655,
            "full_name": "NIYOMUHOZA Samuel",
            "sex": "M",
            "marital_status": "S",
            "nationality": "RW",
            "religion": "ADVENTIST",
            "status": "ACTIVE",
            "department_code": "MBI",
            "account_code": "SMBINIYSA25",
            "profile_complete": True,
        },
        "profile": {
            "academic_level": "GRADUATE",
            "study_mode": "MASTERS",
            "admitted_term_id": "2025/1",
            "high_school_name": "IPRC Ngoma",
            "high_school_combination": "CSC",
            "high_school_location": "Ngoma",
            "secondary_school_aggregate_score": Decimal("80.00"),
        },
    },
    {
        "member": {
            "campus_id": "20241CSC018",
            "internal_id": 100418,
            "full_name": "UWASE Keza",
            "sex": "F",
            "marital_status": "S",
            "nationality": "RW",
            "religion": "ADVENTIST",
            "status": "ACTIVE",
            "department_code": "CSC",
            "email": "k.uwase@student.auca.ac.rw",
            "phone": "+250780000018",
            "account_code": "SCSCUWKE24",
            "profile_complete": True,
        },
        "profile": {
            "academic_level": "UNDERGRADUATE",
            "study_mode": "DAY",
            "admitted_term_id": "2024/1",
            "high_school_name": "Lycée de Kigali",
            "high_school_combination": "MPC",
            "high_school_location": "Kigali",
            "secondary_school_aggregate_score": Decimal("72.00"),
        },
    },
    {
        "member": {
            "campus_id": "20222THE007",
            "internal_id": 100207,
            "full_name": "HAKIZIMANA Patrick",
            "sex": "M",
            "marital_status": "S",
            "nationality": "RW",
            "status": "SUSPENDED",
            "department_code": "THE",
            "account_code": "STHEHAPA22",
            "profile_complete": False,
            "missing_profile_fields": ["phoneNo", "email"],
        },
        "profile": {
            "academic_level": "UNDERGRADUATE",
            "study_mode": "EVENING",
            "admitted_term_id": "2022/2",
        },
    },
]

STAFF = [
    {
        "member": {
            "campus_id": "STF2016BUS008",
            "internal_id": 50016,
            "full_name": "MUKAMANA Grace",
            "sex": "F",
            "marital_status": "M",
            "nationality": "RW",
            "religion": "ADVENTIST",
            "status": "ACTIVE",
            "department_code": "BUS",
            "email": "g.mukamana@auca.ac.rw",
            "phone": "+250788000016",
            "account_code": "STFBUSMUG16",
            "profile_complete": True,
        },
        "profile": {
            "position": "Lecturer",
            "staff_category": "ACADEMIC",
            "employment_type": "FULL_TIME",
            "hire_date": date(2016, 8, 15),
            "office_code": "BUS-210",
        },
    },
    {
        "member": {
            "campus_id": "STF2012REG003",
            "internal_id": 50003,
            "full_name": "HABIMANA Eric",
            "sex": "M",
            "marital_status": "M",
            "nationality": "RW",
            "religion": "ADVENTIST",
            "status": "ACTIVE",
            "department_code": "REG",
            "email": "e.habimana@auca.ac.rw",
            "phone": "+250788000003",
            "account_code": "STFREGHAE12",
            "profile_complete": True,
        },
        "profile": {
            "position": "Registrar Officer",
            "staff_category": "ADMINISTRATIVE",
            "employment_type": "FULL_TIME",
            "hire_date": date(2012, 1, 9),
            "office_code": "REG-104",
        },
    },
    {
        "member": {
            "campus_id": "STF2022SEC001",
            "internal_id": 50022,
            "full_name": "INGABIRE Aline",
            "sex": "F",
            "marital_status": "S",
            "nationality": "RW",
            "status": "ON_LEAVE",
            "department_code": "SEC",
            "email": "a.ingabire@auca.ac.rw",
            "account_code": "STFSECINA22",
            "profile_complete": True,
        },
        "profile": {
            "position": "Security Supervisor",
            "staff_category": "SUPPORT",
            "employment_type": "FULL_TIME",
            "hire_date": date(2022, 3, 1),
            "office_code": "GATE-01",
        },
    },
]


class Command(BaseCommand):
    help = "Load sample student and staff records for gate verification."

    def handle(self, *args, **options):
        for row in STUDENTS:
            member, _ = CampusMember.objects.update_or_create(
                campus_id=row["member"]["campus_id"],
                defaults={**row["member"], "member_type": CampusMember.MemberType.STUDENT},
            )
            StudentProfile.objects.update_or_create(member=member, defaults=row["profile"])
        for row in STAFF:
            member, _ = CampusMember.objects.update_or_create(
                campus_id=row["member"]["campus_id"],
                defaults={**row["member"], "member_type": CampusMember.MemberType.STAFF},
            )
            StaffProfile.objects.update_or_create(member=member, defaults=row["profile"])
        self.stdout.write(self.style.SUCCESS("Sample campus members are loaded."))
