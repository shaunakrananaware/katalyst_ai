"""Build and validate typed edges; all reads use graph adjacency."""
from copy import deepcopy
import networkx as nx
from backend.graph.schema import EDGE_TYPES
from backend.mock_data.seed_data import DATA

def build_graph(data=None):
    graph = nx.MultiDiGraph()
    for kind, records in (data or DATA).items():
        for record in records:
            if record['id'] in graph:
                raise ValueError('Duplicate node id')
            graph.add_node(record['id'], **deepcopy(record), type=kind)
    def edge(source, target, kind):
        expected = EDGE_TYPES[kind]
        if target not in graph or (graph.nodes[source]['type'], graph.nodes[target]['type']) != expected:
            raise ValueError(f'Invalid {kind} edge: {source} -> {target}')
        graph.add_edge(source, target, type=kind)
    for nid, node in list(graph.nodes(data=True)):
        kind = node['type']
        if kind == 'person': edge(nid, node['org_id'], 'WORKS_AT')
        elif kind == 'lead':
            edge(nid, node['org_id'], 'BELONGS_TO')
            edge(nid, node['owner_id'], 'OWNED_BY')
        elif kind == 'meeting':
            edge(nid, node['lead_id'], 'FOR_LEAD')
            for person in node['attendee_person_ids']: edge(nid, person, 'ATTENDED_BY')
        elif kind == 'note': edge(nid, node['meeting_id'], 'NOTE_OF')
        elif kind == 'email':
            edge(nid, node['lead_id'], 'ABOUT_LEAD')
            edge(nid, node['from_person_id'], 'SENT_BY')
            for person in node['to_person_ids']: edge(nid, person, 'SENT_TO')
    return nx.freeze(graph)
