import copy

from rdflib import Graph
from rdflib.term import BNode


def singleton(s):
    return next(iter(s))


def set_prop(el, key, prop):
    if key not in el:
        el[key] = set()

    el[key].add(prop)


def set_domain(n, p, e, cp):
    domain = singleton(n[p])
    prop = [e]
    if 'range' in n:
        prop.append(next(iter(n['range'])))

    set_prop(cp[domain], 'out', tuple(prop))


def set_range(n, p, e, cp):
    rn = singleton(n[p])
    if rn not in cp:
        return
    else:
        dom = cp[rn]
    prop = [e]
    if 'domain' in n:
        prop.insert(0, next(iter(n['domain'])))

    set_prop(cp[rn], 'in', tuple(prop))


def set_property_restriction(n, cp, e, g):
    prop = singleton(n['onProperty'])
    for pp in n:
        if pp in ['onProperty', 'type']:
            continue
        if pp not in cp[prop]:
            cp[prop][pp] = set()

        cp[prop][pp].update(n[pp])


def load_g(g):
    ont = dict()
    for s, p, o in g:
        sl = str(s).split('#')[-1]
        pl = str(p).split('#')[-1]
        ol = str(o).split('#')[-1]

        if not sl in ont:
            ont[sl] = dict()

        if not pl in ont[sl]:
            ont[sl][pl] = set()

        ont[sl][pl].add(ol)

        if type(s) is BNode:
            if 'type' not in ont[sl]:
                ont[sl]['type'] = set()
            ont[sl]['type'].add('BNode')

    cp = copy.deepcopy(ont)

    for e in cp:
        n = cp[e]
        for p in n:
            if p == 'subClassOf':

                for s in n[p]:
                    if s == 'Thing':
                        continue
                    set_prop(cp[s], 'superClassOf', e)

            elif p == 'type' and 'Restriction' in n[p] and 'onProperty' in n:
                set_property_restriction(n, cp, e, g)
                pass

    for e in ont:
        if p == 'type' and 'Restriction' in n[p] and 'onProperty' in n:

            for s, p, o in g.triples((None, None, BNode(e))):
                s = str(s).split('#')[-1]
                p = str(p).split('#')[-1]
                o = str(o).split('#')[-1]

                cp[s][p].remove(o)

            cp.pop(e)

        n = ont[e]
        for p in n:
            if p == 'domain':
                set_domain(n, p, e, cp)
            elif p == 'range':
                set_range(n, p, e, cp)

            elif p in ['unionOf', 'oneOf', 'intersectionOf', 'distinctMembers', 'members']:
                w = singleton(n[p])
                v = []
                while w != 'nil':
                    cp.pop(w)
                    v.append(singleton(ont[w]['first']))
                    w = singleton(ont[w]['rest'])

                cp[e][p] = v

    return cp, g


def load_ont(path):
    g = Graph()
    g.parse(path)
    return load_g(g)
