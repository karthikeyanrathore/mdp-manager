"""Routing policies seeded into the demo project by `run.py`.

Each entry is the body of a `POST /projects/{id}/routing-policies/`. The
`description` is what the router actually reads, so the "Does not cover ..."
tail on each one is load-bearing: it is how a policy tells Arch-Router to keep
its hands off the neighbouring topics.
"""

ROUTING_POLICIES = [
    {
        "name": "BTU_Portal",
        "description": (
            "Handles academic and administrative questions about studying at BTU Cottbus-Senftenberg, "
            "such as exam registration, exam results, enrollment/re-registration, and module or grading "
            "questions. Does not cover visa, residence permit, work authorization, date/schedule, "
            "mensa/food, or accommodation topics."
        ),
    },
    {
        "name": "BTU_Calendar",
        "description": (
            "Handles questions about dates and schedules at BTU Cottbus-Senftenberg, such as exam dates, "
            "course timetables, semester start/end dates, and registration deadlines. "
            "Does not cover visa, residence permit, mensa/food, or accommodation topics."
        ),
    },
    {
        "name": "Auslander_Cottbus",
        "description": (
            "Handles questions about international students' visa and residency status in Germany, "
            "such as applying for or extending a student visa, changing visa/residence permit status, "
            "rules on part-time work or freelancing while on a student visa, and required documents "
            "or appointments with the Ausländerbehörde. Does not cover academic matters, dates, mensa/food, "
            "or accommodation topics."
        ),
    },
    {
        "name": "BTU_Mensa",
        "description": (
            "Handles questions about the BTU Cottbus-Senftenberg mensa (cafeteria), such as today's or "
            "this week's food menu, meal prices, opening hours, and dietary/allergen information. "
            "Does not cover exam, visa, academic scheduling, or accommodation topics."
        ),
    },
    {
        "name": "Accomodation_Cottbus",
        "description": (
            "Handles questions about housing and accommodation in Cottbus, such as subletting a room or "
            "apartment, finding or offering housing, terminating a lease or moving out, roommate "
            "arrangements, and rental contract questions. Does not cover exam, visa, mensa/food, "
            "or academic scheduling topics."
        ),
    },
]
