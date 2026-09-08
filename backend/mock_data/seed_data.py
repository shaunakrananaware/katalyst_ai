"""Entirely fictional CRM snapshot as of 2026-09-08; all amounts USD."""

from datetime import datetime, timedelta

ORGANIZATIONS = [
    {"id": "org-katalyst", "name": "Katalyst", "industry": "Sales software"},
    *[
        {"id": f"org-{slug}", "name": name, "industry": industry}
        for slug, name, industry in [
            ("figma", "Figma", "Design software"),
            ("notion", "Notion", "Productivity"),
            ("linear", "Linear", "Developer tools"),
            ("acme-cloud", "Acme Cloud", "Cloud infrastructure"),
            ("acme-labs", "Acme Labs", "Research"),
            ("vercel", "Vercel", "Developer tools"),
        ]
    ],
]
PEOPLE = [
    {
        "id": "person-rep",
        "name": "Maya Patel",
        "email": "maya@katalyst.example",
        "role": "Account Executive",
        "org_id": "org-katalyst",
    }
]
for slug, name, role in [
    ("figma", "Elena Park", "VP Design Operations"),
    ("notion", "Jon Bell", "VP Operations"),
    ("linear", "Priya Shah", "Engineering Director"),
    ("acme-cloud", "Alex Chen", "CFO"),
    ("acme-labs", "Alex Cheng", "Research Director"),
    ("vercel", "Sam Rivera", "VP Engineering"),
]:
    PEOPLE.append(
        {
            "id": f"person-{slug}",
            "name": name,
            "email": f"{slug}@prospect.example",
            "role": role,
            "org_id": f"org-{slug}",
        }
    )

# Each narrative describes a distinct outcome, with concrete evidence for synthesis.
SPECS = [
    (
        "figma",
        "Figma - Enterprise Plan",
        "closed_lost",
        120000,
        "2026-08-18",
        "budget",
        "Elena reported that the Q3 budget was frozen after the VP Engineering departure. The pilot reduced manual reporting by 20 percent, but no executive could authorize the annual contract. Procurement declined a phased rollout because the freeze covered new vendors. Revisit in November when the new VP sets the budget.",
    ),
    (
        "notion",
        "Notion - Sales Workspace",
        "closed_won",
        96000,
        "2026-09-02",
        None,
        "Jon secured the CFO as an executive sponsor before the pilot. The team measured six hours saved per rep each week against an agreed baseline. Security approved SSO during the trial rather than at signature. Procurement signed the annual contract with a September onboarding date.",
    ),
    (
        "linear",
        "Linear - Revenue Insights",
        "closed_won",
        72000,
        "2026-07-14",
        None,
        "Priya ran a two-week pilot with ten account managers. Agreed success criteria required cutting handoff time by 30 percent and the pilot achieved 35 percent. A named champion coordinated security review in parallel. The buyer approved the annual subscription and a staged rollout.",
    ),
    (
        "vercel",
        "Vercel - Enterprise Analytics",
        "closed_won",
        150000,
        "2026-06-22",
        None,
        "Sam aligned finance and engineering on a shared ROI worksheet. The pilot demonstrated twelve hours saved per team per month. Legal reviewed the standard terms before the final demo. Finance approved the annual amount and requested onboarding for three teams.",
    ),
    (
        "acme-cloud",
        "Acme Cloud - Revenue Platform",
        "closed_lost",
        84000,
        "2026-08-05",
        "security requirements",
        "Alex required EU-only data residency and customer-managed encryption keys. Our current plan could not meet the encryption requirement before their September audit. Security rejected an exception despite positive user feedback. Acme Cloud selected a vendor with the required controls already available.",
    ),
    (
        "acme-labs",
        "Acme Labs - Research CRM",
        "closed_lost",
        48000,
        "2026-05-28",
        "no executive sponsor",
        "Alex liked the contact summaries but could not secure an executive sponsor. The research team had no agreed success metric for the pilot. The COO prioritized a lab inventory migration and stopped the purchase. A future attempt needs leadership commitment and measurable outcomes before another trial.",
    ),
    (
        "figma",
        "Figma - Team Expansion",
        "prospect",
        64000,
        None,
        None,
        "Elena is exploring a separately funded design-team expansion for next year. The team wants automated account summaries and shared meeting history. No budget approval or purchase commitment exists yet. A discovery workshop is scheduled for September 15 to confirm scope.",
    ),
    (
        "vercel",
        "Vercel - Partner Workspace",
        "prospect",
        110000,
        None,
        None,
        "Sam introduced the partner operations team for a separate workspace. They need a consolidated timeline across partner emails and meetings. The proposed annual amount is an estimate pending discovery. The next step is a September 16 workshop with partner operations.",
    ),
]
LEADS, MEETINGS, NOTES, EMAILS = [], [], [], []
for i, (slug, name, stage, amount, close, loss, narrative) in enumerate(SPECS, 1):
    lid = f"lead-{i}"
    anchor = datetime.fromisoformat(close or "2026-09-07")
    LEADS.append(
        {
            "id": lid,
            "name": name,
            "org_id": f"org-{slug}",
            "stage": stage,
            "amount": amount,
            "currency": "USD",
            "created_date": (anchor - timedelta(days=65)).date().isoformat(),
            "closed_date": close,
            "loss_reason": loss,
            "owner_id": "person-rep",
        }
    )
    for j, days in enumerate((21, 1), 1):
        stamp = (anchor - timedelta(days=days)).strftime("%Y-%m-%dT10:00:00Z")
        mid = f"meeting-{i}-{j}"
        MEETINGS.append(
            {
                "id": mid,
                "lead_id": lid,
                "title": f'{name}: {"discovery" if j == 1 else "decision review"}',
                "datetime": stamp,
                "attendee_person_ids": ["person-rep", f"person-{slug}"],
            }
        )
        note = (
            narrative
            if j == 2
            else (
                f"The team reviewed the scope for {name}. The proposed annual value was USD {amount:,}. "
                "Maya asked the buyer to identify budget ownership and security requirements. "
                "The buyer agreed to a decision review after internal feedback."
            )
        )
        NOTES.append(
            {"id": f"note-{i}-{j}", "meeting_id": mid, "text": note, "source": "Notion"}
        )
        EMAILS.append(
            {
                "id": f"email-{i}-{j}",
                "lead_id": lid,
                "thread_id": f"thread-{i}",
                "from_person_id": f"person-{slug}",
                "to_person_ids": ["person-rep"],
                "subject": f"Re: {name}",
                "body": note,
                "sent_at": stamp,
                "source": "Gmail",
            }
        )

DATA = {
    "organization": ORGANIZATIONS,
    "person": PEOPLE,
    "lead": LEADS,
    "meeting": MEETINGS,
    "note": NOTES,
    "email": EMAILS,
}
