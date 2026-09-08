from copy import deepcopy
import numpy as np
import pytest
from backend import tools
from backend.graph.build_graph import build_graph
from backend.mock_data.seed_data import DATA
from backend.retrieval.embeddings import LazyRetriever


def test_seed_graph_and_multihop():
    assert tools.GRAPH.number_of_nodes() == 70
    assert tools.GRAPH.number_of_edges() == 135
    assert len([n for _, n in tools.GRAPH.nodes(data=True) if n['type'] == 'lead']) == 8
    for lead in DATA['lead']:
        meetings = tools.get_meetings_for_lead(lead['id'])
        assert len(meetings) == 2
        assert len(tools.get_emails_for_lead(lead['id'])) == 2
        for meeting in meetings:
            assert tools.get_notes_for_meeting(meeting['id'])['notes']
        if lead['stage'] == 'closed_lost': assert lead['loss_reason']
    org = tools.get_org_context('org-figma')
    assert [p['name'] for p in org['people']] == ['Elena Park']
    assert {d['id'] for d in org['leads']} == {'lead-1', 'lead-7'}
    # Rep org has no direct prospect leads: this result requires traversal via people.
    assert len(tools.get_org_context('org-katalyst')['leads']) == 8


def test_resolution_and_read_only_copies():
    assert tools.resolve_entity('Acme', 'organization')['status'] == 'ambiguous'
    assert tools.resolve_entity('Alex', 'person')['status'] == 'ambiguous'
    assert tools.resolve_entity('Figma', 'lead')['status'] == 'ambiguous'
    assert tools.resolve_entity('Figm', 'organization')['entity']['id'] == 'org-figma'
    assert tools.resolve_entity('Acme Cloud', 'organization')['entity']['id'] == 'org-acme-cloud'
    assert tools.resolve_entity('zzzzzzzz', 'lead')['status'] == 'not_found'
    record = tools.get_lead_details('lead-1'); record['amount'] = 1
    assert tools.get_lead_details('lead-1')['amount'] == 120000


def test_structured_rank_and_comparison():
    prospects = tools.rank_leads(stage='prospect')
    assert [n['amount'] for n in prospects] == [110000, 64000]
    last = tools.rank_leads(stage='closed', order_by='closed_date', limit=1)[0]
    assert (last['name'], last['amount'], last['closed_date']) == ('Notion - Sales Workspace', 96000, '2026-09-02')
    groups = tools.compare_deal_groups({'stage': 'closed_won'}, {'stage': 'closed_lost'})
    assert groups['group_a']['count'] == groups['group_b']['count'] == 3
    assert groups['group_a']['total_amount'] == 318000
    assert groups['group_b']['total_amount'] == 252000
    assert all(len(d['evidence']) == 4 for d in groups['group_b']['deals'])
    assert tools.get_meetings_for_lead('lead-1', limit=1)[0]['id'] == 'meeting-1-2'


@pytest.mark.parametrize('fn,args', [
    ('get_lead_details', {'lead_id': 'missing'}),
    ('get_meetings_for_lead', {'lead_id': 'missing'}),
    ('get_notes_for_meeting', {'meeting_id': 'lead-1'}),
    ('get_emails_for_lead', {'lead_id': 'missing'}),
    ('get_org_context', {'org_id': 'missing'}),
    ('semantic_search_lead_text', {'lead_id': 'missing', 'query': 'why'}),
])
def test_unknown_ids(fn, args):
    assert tools.TOOLS[fn](**args)['status'] == 'not_found'


@pytest.mark.parametrize('fn,args', [
    ('resolve_entity', {'query': '', 'entity_type': 'lead'}),
    ('resolve_entity', {'query': 'Figma', 'entity_type': 'invalid'}),
    ('rank_leads', {'limit': 0}), ('rank_leads', {'order_by': 'bogus'}),
    ('rank_leads', {'stage': 'bogus'}),
    ('compare_deal_groups', {'group_a_filter': {'stage': 'closed_won', 'typo': 1}, 'group_b_filter': {'stage': 'closed_lost'}}),
    ('get_meetings_for_lead', {'lead_id': 'lead-1', 'limit': -1}),
])
def test_invalid_inputs(fn, args):
    assert tools.TOOLS[fn](**args)['status'] == 'invalid_input'


def test_tied_latest_requires_clarification(monkeypatch):
    seed = deepcopy(DATA)
    seed['meeting'][0]['datetime'] = seed['meeting'][1]['datetime']
    seed['lead'][0]['closed_date'] = '2026-09-02'
    monkeypatch.setattr(tools, 'GRAPH', build_graph(seed))
    assert tools.get_meetings_for_lead('lead-1', limit=1)['status'] == 'ambiguous'
    assert tools.rank_leads(stage='closed', order_by='closed_date', limit=1)['status'] == 'ambiguous'


def test_lazy_cache_and_cosine():
    class Encoder:
        calls = []
        def embed(self, texts):
            self.calls.append(texts)
            return [np.array([1, 0]) if 'budget' in t else np.array([0, 1]) for t in texts]
    encoder = Encoder()
    retriever = LazyRetriever(lambda: encoder)
    assert retriever.model is None and not retriever.cache
    chunks = [{'id': 'a', 'text': 'budget frozen'}, {'id': 'b', 'text': 'security approval'}]
    assert retriever.search('l1', chunks, 'budget issue', 1)[0]['id'] == 'a'
    assert retriever.search('l1', chunks, 'security issue', 1)[0]['id'] == 'b'
    assert retriever.document_embedding_batches == 1
    assert len(encoder.calls) == 3
    retriever.search('l2', chunks, 'budget', 1)
    assert retriever.document_embedding_batches == 2
