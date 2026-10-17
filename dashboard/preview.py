"""Sample desk figures so the layout can be reviewed.

JP replaces these lists with database queries. The templates already loop
over ``stats``, ``visitors``, and ``events``.
"""

VISITORS = [
    {
        "reference": "AUC-4F2A91",
        "name": "UWASE Keza",
        "phone": "+250780000001",
        "email": "keza@example.com",
        "organization": "Kigali Public Library",
        "destination": "Registrar",
        "host": "HABIMANA Eric",
        "purpose": "Collect a transcript for a job application.",
        "status": "pending",
        "status_label": "Pending",
        "arrived": "15 Oct 2026, 08:12",
        "valid_until": "15 Oct 2026, 16:12",
    },
    {
        "reference": "AUC-91C0DE",
        "name": "MUGISHA David",
        "phone": "+250780000002",
        "email": "david@example.com",
        "organization": "Parent",
        "destination": "Library",
        "host": "INGABIRE Aline",
        "purpose": "Return a borrowed book.",
        "status": "approved",
        "status_label": "Approved",
        "arrived": "15 Oct 2026, 08:26",
        "valid_until": "15 Oct 2026, 16:26",
    },
    {
        "reference": "AUC-77B31A",
        "name": "KANEZA Amina",
        "phone": "+250780000003",
        "email": "",
        "organization": "Bank of Kigali",
        "destination": "Business office",
        "host": "MUKAMANA Grace",
        "purpose": "Meet a lecturer about an internship.",
        "status": "checked_in",
        "status_label": "Checked in",
        "arrived": "15 Oct 2026, 09:04",
        "valid_until": "15 Oct 2026, 17:04",
    },
    {
        "reference": "AUC-B08E22",
        "name": "HAKIZIMANA Jean",
        "phone": "+250780000004",
        "email": "jean@example.com",
        "organization": "Courier",
        "destination": "ICT",
        "host": "HABIMANA Eric",
        "purpose": "Deliver a parcel.",
        "status": "rejected",
        "status_label": "Rejected",
        "arrived": "15 Oct 2026, 09:18",
        "valid_until": "15 Oct 2026, 17:18",
    },
    {
        "reference": "AUC-C33A70",
        "name": "UWIMANA Diane",
        "phone": "+250780000005",
        "email": "diane@example.com",
        "organization": "Ministry of Education",
        "destination": "Dean of students",
        "host": "MUKAMANA Grace",
        "purpose": "Courtesy visit.",
        "status": "pending",
        "status_label": "Pending",
        "arrived": "15 Oct 2026, 09:41",
        "valid_until": "15 Oct 2026, 17:41",
    },
]

EVENTS = [
    {
        "time": "09:04",
        "person": "KANEZA Amina",
        "kind": "Visitor",
        "event": "Entry",
        "result": "accepted",
        "result_label": "Accepted",
        "officer": "Desk",
    },
    {
        "time": "08:41",
        "person": "NIYOMUHOZA Samuel",
        "kind": "Student",
        "event": "Entry",
        "result": "accepted",
        "result_label": "Accepted",
        "officer": "Desk",
    },
    {
        "time": "08:20",
        "person": "MUKAMANA Grace",
        "kind": "Staff",
        "event": "Entry",
        "result": "accepted",
        "result_label": "Accepted",
        "officer": "Desk",
    },
    {
        "time": "08:05",
        "person": "HAKIZIMANA Jean",
        "kind": "Visitor",
        "event": "Entry",
        "result": "rejected",
        "result_label": "Rejected",
        "officer": "Desk",
    },
]


BADGES = {
    "pending": "warning",
    "approved": "success",
    "checked_in": "info",
    "rejected": "danger",
    "accepted": "success",
}


def stats():
    pending = sum(1 for visit in VISITORS if visit["status"] == "pending")
    entries = sum(1 for event in EVENTS if event["event"] == "Entry" and event["result"] == "accepted")
    return [
        {"key": "visitors", "label": "Visitors today", "value": len(VISITORS), "hint": "Registered this morning", "tone": "info", "icon": "fas fa-user-friends"},
        {"key": "pending", "label": "Pending", "value": pending, "hint": "Waiting for the desk", "tone": "warning", "icon": "fas fa-clock"},
        {"key": "entries", "label": "Entries today", "value": entries, "hint": "Accepted at the gate", "tone": "success", "icon": "fas fa-door-open"},
        {"key": "offices", "label": "Active offices", "value": 6, "hint": "Open for visitors", "tone": "primary", "icon": "fas fa-building"},
    ]


def _initials(name):
    parts = [part for part in name.split() if part]
    if len(parts) >= 2:
        return (parts[0][0] + parts[1][0]).upper()
    return (name[:2] or "?").upper()


def _with_badge(row, field):
    tagged = dict(row)
    tagged["badge"] = BADGES[row[field]]
    who = row.get("name") or row.get("person") or ""
    tagged["initials"] = _initials(who)
    return tagged


def mix():
    rows = visitors()
    total = len(rows) or 1
    order = (
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("checked_in", "Checked in"),
        ("rejected", "Rejected"),
    )
    result = []
    for key, label in order:
        count = sum(1 for visit in rows if visit["status"] == key)
        result.append(
            {
                "key": key,
                "label": label,
                "count": count,
                "share": round(count * 100 / total),
                "badge": BADGES[key],
            }
        )
    return result


def trend():
    """Accepted entries by hour, from the sample gate log."""
    hours = ["07", "08", "09", "10", "11", "12"]
    counts = {hour: 0 for hour in hours}
    for event in EVENTS:
        if event["result"] != "accepted":
            continue
        hour = event["time"].split(":")[0]
        if hour in counts:
            counts[hour] += 1
    peak = max(counts.values()) or 1
    bars = []
    for hour in hours:
        count = counts[hour]
        bars.append(
            {
                "label": hour,
                "count": count,
                "height": round(count * 100 / peak) if count else 8,
                "empty": count == 0,
            }
        )
    return bars


def visitors():
    return [_with_badge(visit, "status") for visit in VISITORS]


def visitor(reference):
    key = (reference or "").upper()
    for visit in visitors():
        if visit["reference"] == key:
            return visit
    return None


def events():
    return [_with_badge(event, "result") for event in EVENTS]
