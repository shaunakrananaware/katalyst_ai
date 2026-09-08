"""Typed graph vocabulary; amounts are integer USD, timestamps are ISO UTC."""
from enum import Enum

class NodeType(str, Enum):
    ORGANIZATION = 'organization'
    PERSON = 'person'
    LEAD = 'lead'
    MEETING = 'meeting'
    NOTE = 'note'
    EMAIL = 'email'

EDGE_TYPES = {
    'WORKS_AT': ('person', 'organization'),
    'BELONGS_TO': ('lead', 'organization'),
    'OWNED_BY': ('lead', 'person'),
    'FOR_LEAD': ('meeting', 'lead'),
    'ATTENDED_BY': ('meeting', 'person'),
    'NOTE_OF': ('note', 'meeting'),
    'ABOUT_LEAD': ('email', 'lead'),
    'SENT_BY': ('email', 'person'),
    'SENT_TO': ('email', 'person'),
}
STAGES = {'prospect', 'negotiation', 'closed_won', 'closed_lost'}
