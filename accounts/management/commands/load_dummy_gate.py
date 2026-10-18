from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import CampusMember, CheckIn, StaffProfile, StudentProfile
from gatepass.models import GateEvent, VisitorVisit

EXTRA_STUDENTS = [
    {
        "member": {
            "campus_id": "20231NUR012",
            "full_name": "UWIMANA Diane",
            "status": "ACTIVE",
            "department_code": "NUR",
            "email": "d.uwimana@student.auca.ac.rw",
            "phone": "+250781110012",
        },
        "profile": {"academic_level": "UNDERGRADUATE", "study_mode": "DAY"},
    },
    {
        "member": {
            "campus_id": "20211ACC004",
            "full_name": "MUGISHA Jean",
            "status": "ACTIVE",
            "department_code": "ACC",
            "email": "j.mugisha@student.auca.ac.rw",
            "phone": "+250781110004",
        },
        "profile": {"academic_level": "UNDERGRADUATE", "study_mode": "WEEKEND"},
    },
    {
        "member": {
            "campus_id": "20201BIT021",
            "full_name": "IRADUKUNDA Marie",
            "status": "GRADUATED",
            "department_code": "BIT",
            "email": "m.iradukunda@student.auca.ac.rw",
        },
        "profile": {"academic_level": "UNDERGRADUATE", "study_mode": "DAY"},
    },
]

EXTRA_STAFF = [
    {
        "member": {
            "campus_id": "STF2018NUR006",
            "full_name": "UWASE Claudine",
            "status": "ACTIVE",
            "department_code": "NUR",
            "email": "c.uwase@auca.ac.rw",
            "phone": "+250788110006",
        },
        "profile": {
            "position": "Campus Nurse",
            "staff_category": "SUPPORT",
            "employment_type": "FULL_TIME",
            "office_code": "NUR-01",
        },
    },
    {
        "member": {
            "campus_id": "STF2019CSC011",
            "full_name": "NKURUNZIZA David",
            "status": "ACTIVE",
            "department_code": "CSC",
            "email": "d.nkurunziza@auca.ac.rw",
            "phone": "+250788110011",
        },
        "profile": {
            "position": "Lecturer",
            "staff_category": "ACADEMIC",
            "employment_type": "FULL_TIME",
            "office_code": "CSC-12",
        },
    },
    {
        "member": {
            "campus_id": "STF2020ACC002",
            "full_name": "KAYITESI Hope",
            "status": "ACTIVE",
            "department_code": "ACC",
            "email": "h.kayitesi@auca.ac.rw",
            "phone": "+250788110002",
        },
        "profile": {
            "position": "Accountant",
            "staff_category": "ADMINISTRATIVE",
            "employment_type": "CONTRACT",
            "office_code": "ACC-03",
        },
    },
]

VISITORS = [
    {
        "reference_number": "AUC-SAMPLE0001",
        "first_name": "Amina",
        "last_name": "Uwase",
        "phone": "+250788220001",
        "organization": "City Library",
        "destination": "Registrar Office",
        "host_name": "Eric Habimana",
        "purpose": "Collect a transcript",
        "status": VisitorVisit.Status.PENDING,
    },
    {
        "reference_number": "AUC-SAMPLE0002",
        "first_name": "Jean",
        "last_name": "Bosco",
        "phone": "+250788220002",
        "organization": "Ministry of Education",
        "destination": "Registrar Office",
        "host_name": "Grace Mukamana",
        "purpose": "A scheduled meeting",
        "status": VisitorVisit.Status.APPROVED,
    },
    {
        "reference_number": "AUC-SAMPLE0003",
        "first_name": "Claire",
        "last_name": "Ingabire",
        "phone": "+250788220003",
        "organization": "Rwanda Television",
        "destination": "Registrar Office",
        "host_name": "Eric Habimana",
        "purpose": "Campus interview",
        "status": VisitorVisit.Status.CHECKED_IN,
    },
]


class Command(BaseCommand):
    help = "Load dummy students, staff, check-ins, and visitors for desk testing."

    def handle(self, *args, **options):
        self._members()
        bulk_members, bulk_check_ins = self._bulk_people()
        check_ins = self._check_ins() + bulk_check_ins
        visits = self._visits() + self._bulk_visits()
        self.stdout.write(
            self.style.SUCCESS(
                "Dummy gate data ready: "
                f"{bulk_members} extra people, {check_ins} check-ins, and {visits} visits."
            )
        )

    def _members(self):
        for row in EXTRA_STUDENTS:
            member, _ = CampusMember.objects.update_or_create(
                campus_id=row["member"]["campus_id"],
                defaults={**row["member"], "member_type": CampusMember.MemberType.STUDENT},
            )
            StudentProfile.objects.update_or_create(member=member, defaults=row["profile"])
        for row in EXTRA_STAFF:
            member, _ = CampusMember.objects.update_or_create(
                campus_id=row["member"]["campus_id"],
                defaults={**row["member"], "member_type": CampusMember.MemberType.STAFF},
            )
            StaffProfile.objects.update_or_create(member=member, defaults=row["profile"])

    def _check_ins(self):
        now = timezone.now()
        plan = [
            ("20251MBI049", CheckIn.Status.PENDING, now - timedelta(minutes=20), None, None),
            ("20241CSC018", CheckIn.Status.APPROVED, now - timedelta(hours=2), now - timedelta(hours=1, minutes=40), None),
            ("STF2016BUS008", CheckIn.Status.APPROVED, now - timedelta(hours=3), now - timedelta(hours=2, minutes=50), None),
            ("STF2012REG003", CheckIn.Status.CHECKED_OUT, now - timedelta(hours=5), now - timedelta(hours=4, minutes=40), now - timedelta(hours=1)),
            ("STF2018NUR006", CheckIn.Status.PENDING, now - timedelta(minutes=8), None, None),
            ("STF2019CSC011", CheckIn.Status.CHECKED_OUT, now - timedelta(hours=6), now - timedelta(hours=5, minutes=30), now - timedelta(minutes=40)),
        ]
        created = 0
        for campus_id, status, arrived, approved, left in plan:
            member = CampusMember.objects.filter(campus_id=campus_id).first()
            if member is None:
                continue
            if CheckIn.objects.filter(member=member, status=status, checked_in_at__gte=now - timedelta(hours=12)).exists():
                continue
            row = CheckIn.objects.create(member=member, status=status)
            CheckIn.objects.filter(pk=row.pk).update(
                checked_in_at=arrived,
                approved_at=approved,
                checked_out_at=left,
                status=status,
            )
            created += 1
        return created

    def _visits(self):
        now = timezone.now()
        officer = get_user_model().objects.filter(is_superuser=True).order_by("id").first()
        ensured = 0
        for row in VISITORS:
            visit, created = VisitorVisit.objects.get_or_create(
                reference_number=row["reference_number"],
                defaults={
                    **row,
                    "valid_until": now + timedelta(hours=8),
                },
            )
            if created:
                VisitorVisit.objects.filter(pk=visit.pk).update(
                    created_at=now - timedelta(minutes=30),
                    status=row["status"],
                )
                visit.refresh_from_db()
            if (
                officer
                and visit.status == VisitorVisit.Status.CHECKED_IN
                and not visit.gate_events.filter(event_type=GateEvent.EventType.ENTRY).exists()
            ):
                GateEvent.objects.create(
                    visit=visit,
                    event_type=GateEvent.EventType.ENTRY,
                    officer=officer,
                    outcome=GateEvent.Outcome.ACCEPTED,
                )
            ensured += 1
        return ensured

    def _bulk_people(self):
        given = [
            "Aline", "Eric", "Diane", "Jean", "Marie", "David", "Hope", "Claudine",
            "Patrick", "Keza", "Samuel", "Grace", "Paul", "Alice", "Olivier", "Chantal",
        ]
        family = [
            "Uwase", "Habimana", "Mukamana", "Niyonsenga", "Iradukunda", "Mugisha",
            "Kayitesi", "Nsengiyumva", "Uwimana", "Hakizimana", "Bizimana", "Ingabire",
        ]
        departments = ["CSC", "BUS", "NUR", "ACC", "BIT", "THE", "REG"]
        levels = ["UNDERGRADUATE", "GRADUATE"]
        modes = ["DAY", "EVENING", "WEEKEND", "MASTERS"]
        positions = ["Lecturer", "Accountant", "Nurse", "Librarian", "Officer"]
        categories = ["ACADEMIC", "ADMINISTRATIVE", "SUPPORT"]
        employment = ["FULL_TIME", "PART_TIME", "CONTRACT"]
        statuses = ["ACTIVE", "ACTIVE", "ACTIVE", "ACTIVE", "SUSPENDED", "ON_LEAVE", "GRADUATED"]
        created = 0
        members = []
        for index in range(1, 29):
            campus_id = f"2024DUM{index:03d}"
            member, was_created = CampusMember.objects.update_or_create(
                campus_id=campus_id,
                defaults={
                    "full_name": f"{given[index % len(given)]} {family[index % len(family)]}",
                    "member_type": CampusMember.MemberType.STUDENT,
                    "status": statuses[index % len(statuses)],
                    "department_code": departments[index % len(departments)],
                    "email": f"student{index}@student.auca.ac.rw",
                    "phone": f"+2507812{index:05d}",
                },
            )
            StudentProfile.objects.update_or_create(
                member=member,
                defaults={
                    "academic_level": levels[index % len(levels)],
                    "study_mode": modes[index % len(modes)],
                },
            )
            created += int(was_created)
            members.append(member)
        for index in range(1, 17):
            campus_id = f"STF24DUM{index:03d}"
            member, was_created = CampusMember.objects.update_or_create(
                campus_id=campus_id,
                defaults={
                    "full_name": f"{given[(index + 5) % len(given)]} {family[(index + 4) % len(family)]}",
                    "member_type": CampusMember.MemberType.STAFF,
                    "status": "ACTIVE" if index % 6 else "ON_LEAVE",
                    "department_code": departments[index % len(departments)],
                    "email": f"staff{index}@auca.ac.rw",
                    "phone": f"+2507883{index:05d}",
                },
            )
            StaffProfile.objects.update_or_create(
                member=member,
                defaults={
                    "position": positions[index % len(positions)],
                    "staff_category": categories[index % len(categories)],
                    "employment_type": employment[index % len(employment)],
                    "office_code": f"{departments[index % len(departments)]}-{index:02d}",
                },
            )
            created += int(was_created)
            members.append(member)
        return created, self._check_ins_for(members)

    def _check_ins_for(self, members):
        now = timezone.now()
        cycle = [CheckIn.Status.PENDING, CheckIn.Status.APPROVED, CheckIn.Status.CHECKED_OUT]
        created = 0
        for index, member in enumerate(members, start=1):
            if CheckIn.objects.filter(member=member).exists():
                continue
            status = cycle[index % len(cycle)]
            arrived = now - timedelta(days=index % 4, hours=index % 12, minutes=12)
            approved = arrived + timedelta(minutes=25) if status != CheckIn.Status.PENDING else None
            left = approved + timedelta(hours=2) if status == CheckIn.Status.CHECKED_OUT else None
            row = CheckIn.objects.create(member=member, status=status)
            CheckIn.objects.filter(pk=row.pk).update(
                checked_in_at=arrived,
                approved_at=approved,
                checked_out_at=left,
                status=status,
            )
            created += 1
        return created

    def _bulk_visits(self):
        now = timezone.now()
        officer = get_user_model().objects.filter(is_superuser=True).order_by("id").first()
        given = ["Amina", "Jean", "Claire", "Peter", "Sarah", "Leon", "Peace", "Yves"]
        family = ["Uwase", "Bosco", "Ingabire", "Habimana", "Mukamana", "Gasana"]
        statuses = [
            VisitorVisit.Status.PENDING,
            VisitorVisit.Status.APPROVED,
            VisitorVisit.Status.CHECKED_IN,
            VisitorVisit.Status.REJECTED,
            VisitorVisit.Status.COMPLETED,
        ]
        ensured = 0
        for index in range(1, 25):
            reference = f"AUC-DUM{index:07d}"
            status = statuses[index % len(statuses)]
            visit, created = VisitorVisit.objects.get_or_create(
                reference_number=reference,
                defaults={
                    "first_name": given[index % len(given)],
                    "last_name": family[index % len(family)],
                    "phone": f"+2507884{index:05d}",
                    "organization": "Sample organisation",
                    "destination": "Registrar Office",
                    "host_name": "Eric Habimana",
                    "purpose": "Dummy visit for desk testing",
                    "status": status,
                    "valid_until": now + timedelta(hours=8),
                },
            )
            if created:
                VisitorVisit.objects.filter(pk=visit.pk).update(
                    created_at=now - timedelta(days=index % 3, hours=index % 8),
                    status=status,
                )
                visit.refresh_from_db()
            if (
                officer
                and visit.status == VisitorVisit.Status.CHECKED_IN
                and not visit.gate_events.filter(event_type=GateEvent.EventType.ENTRY).exists()
            ):
                GateEvent.objects.create(
                    visit=visit,
                    event_type=GateEvent.EventType.ENTRY,
                    officer=officer,
                    outcome=GateEvent.Outcome.ACCEPTED,
                )
            ensured += 1
        return ensured
