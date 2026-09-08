"""Read-only graph tools. Pydantic validates both direct and model-originated calls."""

from copy import deepcopy
from functools import wraps
from typing import Literal
from pydantic import validate_call, ValidationError
from rapidfuzz.fuzz import WRatio
from backend.graph.build_graph import build_graph
from backend.graph.schema import STAGES

GRAPH = build_graph()


def safe(fn):
    validated = validate_call(fn)

    @wraps(fn)
    def wrapped(*args, **kwargs):
        try:
            return validated(*args, **kwargs)
        except (ValidationError, ValueError, TypeError) as exc:
            return {"status": "invalid_input", "message": str(exc).split("\n")[0]}
        except KeyError as exc:
            return {"status": "not_found", "id": str(exc.args[0])}
        except Exception:
            return {
                "status": "unavailable",
                "message": "Retrieval failed. Try again; do not infer missing evidence.",
            }

    return wrapped


def node(nid, kind):
    if nid not in GRAPH or GRAPH.nodes[nid]["type"] != kind:
        raise KeyError(nid)
    return deepcopy(dict(GRAPH.nodes[nid]))


def related(nid, edge_type, incoming=False):
    edges = (
        GRAPH.in_edges(nid, data=True) if incoming else GRAPH.out_edges(nid, data=True)
    )
    ids = {a if incoming else b for a, b, edge in edges if edge["type"] == edge_type}
    return [deepcopy(dict(GRAPH.nodes[i])) for i in sorted(ids)]


def bound(value, maximum=100):
    if value is not None and not 1 <= value <= maximum:
        raise ValueError(f"limit must be 1..{maximum}")


def capped(rows, limit, field):
    # Never silently choose one member of a tied boundary (especially "last").
    if limit and len(rows) > limit and rows[limit - 1][field] == rows[limit][field]:
        tied = [r for r in rows if r[field] == rows[limit - 1][field]]
        return {
            "status": "ambiguous",
            "reason": f"Tied {field} at selection boundary",
            "candidates": tied,
        }
    return rows[:limit] if limit else rows


@safe
def resolve_entity(
    query: str, entity_type: Literal["lead", "organization", "person"]
) -> dict:
    """Resolve a name or exact ID. Multiple close matches require user clarification."""
    query = query.strip().casefold()
    if not query:
        raise ValueError("query must not be empty")
    rows = [dict(n) for _, n in GRAPH.nodes(data=True) if n["type"] == entity_type]
    exact = [n for n in rows if query in (n["id"].casefold(), n["name"].casefold())]
    scored = sorted(
        [(WRatio(query, n["name"].casefold()), n) for n in rows],
        key=lambda x: (-x[0], x[1]["id"]),
    )
    candidates = exact or [
        n for score, n in scored if score >= 70 and score >= scored[0][0] - 8
    ]
    if not candidates:
        return {"status": "not_found", "query": query}
    if len(candidates) > 1:
        return {"status": "ambiguous", "candidates": deepcopy(candidates)}
    return {"status": "resolved", "entity": deepcopy(candidates[0])}


@safe
def get_lead_details(lead_id: str) -> dict:
    """Return authoritative stage, USD amount, dates, loss reason, organization and owner."""
    lead = node(lead_id, "lead")
    return {
        **lead,
        "organization": related(lead_id, "BELONGS_TO")[0],
        "owner": related(lead_id, "OWNED_BY")[0],
    }


@safe
def get_meetings_for_lead(
    lead_id: str, limit: int | None = None, most_recent_first: bool = True
) -> list[dict] | dict:
    """Retrieve meetings by date; tied latest selections return ambiguous candidates."""
    node(lead_id, "lead")
    bound(limit)
    rows = sorted(
        related(lead_id, "FOR_LEAD", True),
        key=lambda n: n["datetime"],
        reverse=most_recent_first,
    )
    return capped(rows, limit, "datetime")


@safe
def get_notes_for_meeting(meeting_id: str) -> dict:
    """Traverse Meeting <- NOTE_OF - Note and return raw notes with source IDs."""
    meeting = node(meeting_id, "meeting")
    return {"meeting": meeting, "notes": related(meeting_id, "NOTE_OF", True)}


@safe
def get_emails_for_lead(lead_id: str, limit: int | None = None) -> list[dict] | dict:
    """Return newest emails first, including full bodies and source metadata."""
    node(lead_id, "lead")
    bound(limit)
    return capped(
        sorted(
            related(lead_id, "ABOUT_LEAD", True),
            key=lambda n: n["sent_at"],
            reverse=True,
        ),
        limit,
        "sent_at",
    )


@safe
def rank_leads(
    stage: str | None = None,
    order_by: Literal["amount", "created_date", "closed_date"] = "amount",
    descending: bool = True,
    limit: int = 5,
) -> list[dict] | dict:
    """Deterministically filter and rank deals. stage='closed' includes won and lost. closed_date excludes open deals. Returns only available records."""
    bound(limit)
    if stage is not None and stage not in STAGES | {"closed"}:
        raise ValueError("Unknown stage")
    rows = [
        dict(n)
        for _, n in GRAPH.nodes(data=True)
        if n["type"] == "lead"
        and (
            stage is None
            or n["stage"] == stage
            or (stage == "closed" and n["closed_date"])
        )
        and n.get(order_by) is not None
    ]
    return capped(
        sorted(rows, key=lambda n: n[order_by], reverse=descending), limit, order_by
    )


def text_chunks(lead_id):
    node(lead_id, "lead")
    chunks = []
    for meeting in related(lead_id, "FOR_LEAD", True):
        for note in related(meeting["id"], "NOTE_OF", True):
            chunks.append(
                {
                    "id": note["id"],
                    "source": "Notion",
                    "meeting_id": meeting["id"],
                    "date": meeting["datetime"],
                    "text": note["text"],
                }
            )
    for email in related(lead_id, "ABOUT_LEAD", True):
        chunks.append(
            {
                "id": email["id"],
                "source": "Gmail",
                "date": email["sent_at"],
                "text": email["body"],
            }
        )
    return chunks


@safe
def compare_deal_groups(
    group_a_filter: dict, group_b_filter: dict, limit_per_group: int = 5
) -> dict:
    """Compare last N deals per stage, with deterministic totals and all supporting notes/emails. Filters accept only stage, e.g. {'stage':'closed_won'}."""
    bound(limit_per_group)
    groups = {}
    for label, criteria in [("group_a", group_a_filter), ("group_b", group_b_filter)]:
        if set(criteria) != {"stage"} or criteria["stage"] not in STAGES:
            raise ValueError("Each filter requires a valid stage only")
        rows = rank_leads(
            stage=criteria["stage"],
            order_by=(
                "closed_date"
                if criteria["stage"].startswith("closed")
                else "created_date"
            ),
            limit=limit_per_group,
        )
        if isinstance(rows, dict):
            return rows
        groups[label] = {
            "filter": criteria,
            "requested_count": limit_per_group,
            "count": len(rows),
            "total_amount": sum(n["amount"] for n in rows),
            "currency": "USD",
            "deals": [{**n, "evidence": text_chunks(n["id"])} for n in rows],
        }
    return groups


@safe
def semantic_search_lead_text(
    lead_id: str, query: str, top_k: int = 3
) -> list[dict] | dict:
    """Lazily compute local semantic embeddings of this lead's notes/emails, cache and return cosine-ranked evidence."""
    bound(top_k)
    if not query.strip():
        raise ValueError("query must not be empty")
    chunks = text_chunks(lead_id)
    from backend.retrieval.embeddings import RETRIEVER

    return RETRIEVER.search(lead_id, chunks, query, top_k)


@safe
def get_org_context(org_id: str) -> dict:
    """Traverse org <- people <- meetings -> leads and org <- leads, including email involvement."""
    org = node(org_id, "organization")
    people = related(org_id, "WORKS_AT", True)
    leads = {n["id"]: n for n in related(org_id, "BELONGS_TO", True)}
    for person in people:
        for meeting in related(person["id"], "ATTENDED_BY", True):
            for lead in related(meeting["id"], "FOR_LEAD"):
                leads[lead["id"]] = lead
        for edge in ("SENT_BY", "SENT_TO"):
            for email in related(person["id"], edge, True):
                for lead in related(email["id"], "ABOUT_LEAD"):
                    leads[lead["id"]] = lead
        for lead in related(person["id"], "OWNED_BY", True):
            leads[lead["id"]] = lead
    return {"organization": org, "people": people, "leads": list(leads.values())}


TOOL_FUNCTIONS = [
    resolve_entity,
    get_lead_details,
    get_meetings_for_lead,
    get_notes_for_meeting,
    get_emails_for_lead,
    rank_leads,
    compare_deal_groups,
    semantic_search_lead_text,
    get_org_context,
]
TOOLS = {fn.__name__: fn for fn in TOOL_FUNCTIONS}
