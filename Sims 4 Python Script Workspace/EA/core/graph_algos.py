from __future__ import annotationsfrom typing import TYPE_CHECKINGif TYPE_CHECKING:
    from typing import Iterable, Callable, List, Any__all__ = ['strongly_connected_components', 'topological_sort']
def topological_sort(node_gen:'Iterable[Any]', parents_gen_fn:'Callable[[Any], Iterable[Any]]', maintain_order:'bool'=False) -> 'List[Any]':
    sccs = strongly_connected_components(node_gen, parents_gen_fn, maintain_order)
    result = []
    for scc in sccs:
        if len(scc) != 1:
            raise ValueError('Graph has a strongly connected cycle ({})'.format(','.join([str(item) for item in scc])))
        result.append(scc[0])
    return result

def strongly_connected_components(node_gen:'Iterable[Any]', parents_gen_fn:'Callable[[Any], Iterable[Any]]', maintain_order:'bool'=False) -> 'List[List[Any]]':
    index = 0
    indices = {}
    lowlinks = {}
    stack = []
    stack_members = set()
    if maintain_order:
        ordered_nodes = tuple(node_gen)
        nodes = set(ordered_nodes)
    else:
        nodes = set(node_gen)
        ordered_nodes = nodes
    sccs = []
    for node in ordered_nodes:
        if node not in indices:
            index = _strongconnect(node, sccs, nodes, parents_gen_fn, indices, lowlinks, stack, stack_members, index)
    return sccs

def _strongconnect(node, sccs, nodes, parents_gen_fn, indices, lowlinks, stack, stack_members, index):
    indices[node] = index
    lowlinks[node] = index
    index += 1
    stack.append(node)
    stack_members.add(node)
    parents = parents_gen_fn(node)
    if parents is not None:
        for parent in parents:
            if parent not in nodes:
                pass
            elif parent not in indices:
                index = _strongconnect(parent, sccs, nodes, parents_gen_fn, indices, lowlinks, stack, stack_members, index)
                lowlinks[node] = min(lowlinks[node], lowlinks[parent])
            elif parent in stack_members:
                lowlinks[node] = min(lowlinks[node], indices[parent])
    if lowlinks[node] == indices[node]:
        scc = []
        sccs.append(scc)
        while True:
            v = stack.pop()
            stack_members.remove(v)
            scc.append(v)
            if v is node:
                break
    return index
