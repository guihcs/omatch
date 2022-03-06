import copy

from rdflib import Graph
from rdflib.term import BNode


def singleton(_set):
    return next(iter(_set))


def set_property(element, key, prop):
    if key not in element:
        element[key] = set()

    element[key].add(prop)


def set_domain(element, prop, value, ontology):
    domain = singleton(element[prop])
    prop = [value]
    if 'range' in element:
        prop.append(next(iter(element['range'])))

    set_property(ontology[domain], 'out', tuple(prop))


def set_range(element, prop, value, ontology):
    rang = singleton(element[prop])
    if rang not in ontology:
        return

    prop = [value]
    if 'domain' in element:
        prop.insert(0, next(iter(element['domain'])))

    set_property(ontology[rang], 'in', tuple(prop))


def set_property_restriction(element, ontology):
    prop = singleton(element['onProperty'])
    for pp in element:
        if pp in ['onProperty', 'type']:
            continue
        if pp not in ontology[prop]:
            ontology[prop][pp] = set()

        ontology[prop][pp].update(element[pp])


def load_g(g):
    ont = dict()
    for s, p, o in g:
        sl = str(s).split('#')[-1]
        pl = str(p).split('#')[-1]
        ol = str(o).split('#')[-1]

        if  sl not in ont:
            ont[sl] = dict()

        if  pl not in ont[sl]:
            ont[sl][pl] = set()

        ont[sl][pl].add(ol)

        if type(s) is BNode:
            if 'type' not in ont[sl]:
                ont[sl]['type'] = set()
            ont[sl]['type'].add('BNode')

    cp = copy.deepcopy(ont)

    set_superclass(cp, g)

    set_refs(cp, g, ont)

    return cp, g


def set_refs(cp, g, ont):
    for e in ont:

        n = ont[e]
        for p in n:
            if p == 'type' and 'Restriction' in n[p] and 'onProperty' in n:

                for s, p, o in g.triples((None, None, BNode(e))):
                    s = str(s).split('#')[-1]
                    p = str(p).split('#')[-1]
                    o = str(o).split('#')[-1]

                    cp[s][p].remove(o)

                cp.pop(e)
            elif p == 'domain':
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


def set_superclass(cp, g):
    for e in cp:
        n = cp[e]
        for p in n:
            if p == 'subClassOf':

                for s in n[p]:
                    if s == 'Thing':
                        continue
                    set_property(cp[s], 'superClassOf', e)

            elif p == 'type' and 'Restriction' in n[p] and 'onProperty' in n:
                set_property_restriction(n, cp)
                pass


def load_ont(path):
    g = Graph()
    g.parse(path)
    return load_g(g)
