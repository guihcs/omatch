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
    range = singleton(n[p])
    if range not in cp:
        return
    else:
        dom = cp[range]
    prop = [e]
    if 'domain' in n:
        prop.insert(0, next(iter(n['domain'])))

    set_prop(cp[range], 'in', tuple(prop))


def set_property_restriction(n, cp):
    prop = singleton(n['onProperty'])
    for pp in n:
        if pp in ['onProperty', 'type']:
            continue
        if pp not in cp[prop]:
            cp[prop][pp] = set()

        cp[prop][pp].update(n[pp])


def g2dict(g):
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

    return ont

def load_g(g):

    ont = g2dict(g)
    cp = copy.deepcopy(ont)

    for e in cp:
        n = cp[e]
        for p in n:
            if p == 'subClassOf':

                for s in n[p]:
                    if s == 'Thing':
                        continue
                    set_prop(cp[s], 'superClassOf', e)

            # elif p == 'type' and 'Restriction' in n[p] and 'onProperty' in n:
            #     set_property_restriction(n, cp)
            #     pass

    for e in ont:

        if 'type' not in ont[e]:
            set_prop(cp[e], 'type', 'Misc')

        # if 'type' in ont[e] and 'Restriction' in ont[e]['type'] and 'onProperty' in ont[e]:
        #
        #     for s, p, o in g.triples((None, None, BNode(e))):
        #         s = str(s).split('#')[-1]
        #         p = str(p).split('#')[-1]
        #         o = str(o).split('#')[-1]
        #
        #         print(s, p, o)
        #         cp[s][p].remove(o)
        #
        #     cp.pop(e)
        #     continue

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

    return cp


def load_ont(path):
    g = Graph()
    g.parse(path)
    return load_g(g)


def split_entity(e):
    split = []
    sp = ''
    for i in range(len(e)):
        if e[i].islower() and i + 1 < len(e) and e[i + 1].isupper():
            sp += e[i]
            split += [sp.lower()]
            sp = ''
            continue

        if e[i] == '_' or e[i] == '-':
            split += [sp.lower()]
            sp = ''
            continue
        sp += e[i]
    split += [sp.lower()]
    return split



def namespace(graph):
    for p, n in graph.namespaces():
        if not p:
            return str(n)

    raise Exception('Namespace not found')