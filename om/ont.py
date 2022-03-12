import copy

from rdflib import Graph
from rdflib.term import BNode
from termcolor import colored


def print_node(e, ont, cl=0, ml=2):
    print('\t' * cl, colored(e, attrs=['bold']))
    if cl >= ml:
        return
    if e not in ont:
        return
    n = ont[e]
    for p in n:
        print('\t' * (cl + 1), colored(p, 'cyan'))

        for q in n[p]:
            print_node(q, ont, cl=cl + 2, ml=ml)


def singleton(s):
    return next(iter(s))


def set_prop(el, key, value):
    if key not in el:
        el[key] = set()

    el[key].add(value)


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
        if pp in ['onProperty', 'type', 'superClassOf']:
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

        if sl not in ont:
            ont[sl] = dict()

        if pl not in ont[sl]:
            ont[sl][pl] = set()

        ont[sl][pl].add(ol)

        if type(s) is BNode:
            if 'type' not in ont[sl]:
                ont[sl]['type'] = set()
            ont[sl]['type'].add('BNode')

    return ont


def ref_BNode(n, ont, ignore=None):
    for p in ont[n]:
        for v in ont[n][p]:
            if v not in ont:
                continue
            if ignore is not None and v in ignore:
                continue
            if 'type' not in ont[v]:
                ont[v]['type'] = {'Misc'}
            if 'BNode' in ont[v]['type']:
                return True
    return False


def first_ref(n, ont):
    for p in ont[n]:
        for v in ont[n][p]:
            if v not in ont:
                continue
            if 'BNode' in ont[v]['type']:
                return p, v
    return None


def loop_sequence(s, ont):
    vals = set()
    seq = [s]
    while s != 'nil':
        vals.update(ont[s]['first'])
        s = singleton(ont[s]['rest'])
        seq.append(s)
    return vals, seq


def list_head(start, g, ont):
    while True:
        lw = list(g.triples((None, None, BNode(start))))[0]
        start = str(lw[0].split('#')[-1])
        if 'first' not in ont[start]:
            break

    return start


def load_g(g):
    ont = g2dict(g)

    q = list(ont)
    removed = set()
    solved = set()
    nc = dict()

    while len(q) > 0:
        n = q.pop()

        if 'type' not in ont[n]:
            ont[n]['type'] = {'Misc'}

        if ref_BNode(n, ont, ignore=solved):
            q.insert(0, n)
        else:

            if 'BNode' not in ont[n]['type'] or n in removed:
                continue

            if 'rest' in ont[n] and 'first' in ont[n]:
                s = str(list(g.triples((None, None, BNode(n))))[0][0])
                if 'first' in ont[s]:
                    ont[s]['first'].update(ont[n]['first'])
                    ont[s]['rest'] = {'nil'}

                else:
                    for p in ont[s]:
                        if n in ont[s][p]:
                            ont[s][p] = ont[n]['first']

                removed.add(n)
                solved.add(n)
            elif 'someValuesFrom' in ont[n] and 'Restriction' in ont[n]['type']:
                prop = singleton(ont[n]['onProperty'])
                r = singleton(ont[n]['someValuesFrom'])
                for sl, pl, ol in g.triples((None, None, BNode(n))):
                    sl = str(sl).split('#')[-1]
                    pl = str(pl).split('#')[-1]
                    ol = str(ol).split('#')[-1]
                    if 'first' in ont[sl]:
                        sl = list_head(sl, g, ont)
                        if sl in removed:
                            sl = nc[sl]
                        ont[sl].setdefault('someValuesFrom', set()).add((prop, r))

                    else:

                        ont[sl][pl].remove(n)
                        ont[sl].setdefault('someValuesFrom', set()).add((prop, r))

                removed.add(n)
                solved.add(n)
            elif 'allValuesFrom' in ont[n] and 'Restriction' in ont[n]['type']:
                prop = singleton(ont[n]['onProperty'])
                r = singleton(ont[n]['allValuesFrom'])
                for sl, pl, ol in g.triples((None, None, BNode(n))):
                    sl = str(sl).split('#')[-1]
                    pl = str(pl).split('#')[-1]
                    ol = str(ol).split('#')[-1]
                    if 'first' in ont[sl]:

                        sl = list_head(sl, g, ont)
                        if sl in removed:
                            sl = nc[sl]
                        ont[sl].setdefault('allValuesFrom', set()).add((prop, r))

                    else:
                        ont[sl][pl].remove(n)
                        ont[sl].setdefault('allValuesFrom', set()).add((prop, r))

                removed.add(n)
                solved.add(n)
            elif 'oneOf' in ont[n]:
                new_name = 'OneOf' + '_'.join(list(ont[n]['oneOf']))
                ont[new_name] = ont[n]
                nc[n] = new_name
                for sl, pl, ol in g.triples((None, None, BNode(n))):
                    sl = str(sl).split('#')[-1]
                    pl = str(pl).split('#')[-1]
                    ol = str(ol).split('#')[-1]

                    ont[sl][pl].add(new_name)
                    ont[sl][pl].remove(n)

                removed.add(n)
                solved.add(n)
                solved.add(new_name)
            elif 'unionOf' in ont[n]:
                new_name = 'UnionOf' + '_'.join(list(ont[n]['unionOf']))
                ont[new_name] = ont[n]
                nc[n] = new_name
                for sl, pl, ol in g.triples((None, None, BNode(n))):
                    sl = str(sl).split('#')[-1]
                    pl = str(pl).split('#')[-1]
                    ol = str(ol).split('#')[-1]

                    ont[sl][pl].add(new_name)
                    ont[sl][pl].remove(n)

                removed.add(n)
                solved.add(n)
                solved.add(new_name)
            elif 'intersectionOf' in ont[n]:
                new_name = 'IntersectionOf' + '_'.join(list(ont[n]['intersectionOf']))
                ont[new_name] = ont[n]
                nc[n] = new_name
                for sl, pl, ol in g.triples((None, None, BNode(n))):
                    sl = str(sl).split('#')[-1]
                    pl = str(pl).split('#')[-1]
                    ol = str(ol).split('#')[-1]

                    ont[sl][pl].add(new_name)
                    ont[sl][pl].remove(n)

                removed.add(n)
                solved.add(n)
                solved.add(new_name)
            elif 'cardinality' in ont[n]:
                prop = singleton(ont[n]['onProperty'])
                r = singleton(ont[n]['cardinality'])

                for sl, pl, ol in g.triples((None, None, BNode(n))):
                    sl = str(sl).split('#')[-1]
                    pl = str(pl).split('#')[-1]
                    ol = str(ol).split('#')[-1]

                    ont[sl][pl].remove(n)
                    ont[sl].setdefault('cardinality', set()).add((prop, r))

                removed.add(n)
                solved.add(n)
            elif 'minCardinality' in ont[n]:
                prop = singleton(ont[n]['onProperty'])
                r = singleton(ont[n]['minCardinality'])

                for sl, pl, ol in g.triples((None, None, BNode(n))):
                    sl = str(sl).split('#')[-1]
                    pl = str(pl).split('#')[-1]
                    ol = str(ol).split('#')[-1]

                    ont[sl][pl].remove(n)
                    ont[sl].setdefault('maxCardinality', set()).add((prop, r))

                removed.add(n)
                solved.add(n)
            elif 'maxCardinality' in ont[n]:
                prop = singleton(ont[n]['onProperty'])
                r = singleton(ont[n]['maxCardinality'])

                for sl, pl, ol in g.triples((None, None, BNode(n))):
                    sl = str(sl).split('#')[-1]
                    pl = str(pl).split('#')[-1]
                    ol = str(ol).split('#')[-1]

                    ont[sl][pl].remove(n)
                    ont[sl].setdefault('maxCardinality', set()).add((prop, r))

                removed.add(n)
                solved.add(n)

            elif 'complementOf' in ont[n]:
                new_name = 'ComplementOf' + '_'.join(list(ont[n]['complementOf']))
                ont[new_name] = ont[n]
                nc[n] = new_name
                for sl, pl, ol in g.triples((None, None, BNode(n))):
                    sl = str(sl).split('#')[-1]
                    pl = str(pl).split('#')[-1]
                    ol = str(ol).split('#')[-1]

                    ont[sl][pl].add(new_name)
                    ont[sl][pl].remove(n)

                removed.add(n)
                solved.add(n)
                solved.add(new_name)
            elif 'distinctMembers' in ont[n]:
                new_name = 'DistinctMembers' + '_'.join(list(ont[n]['distinctMembers']))
                ont[new_name] = ont[n]
                nc[n] = new_name
                for sl, pl, ol in g.triples((None, None, BNode(n))):
                    sl = str(sl).split('#')[-1]
                    pl = str(pl).split('#')[-1]
                    ol = str(ol).split('#')[-1]

                    ont[sl][pl].add(new_name)
                    ont[sl][pl].remove(n)

                removed.add(n)
                solved.add(n)
                solved.add(new_name)

            elif 'qualifiedCardinality' in ont[n] and 'Restriction' in ont[n]['type']:
                prop = singleton(ont[n]['onProperty'])
                r = singleton(ont[n]['qualifiedCardinality'])
                ql = singleton(set(ont[n]).difference({'onProperty', 'type', 'qualifiedCardinality'}))
                ql = singleton(ont[n][ql])
                for sl, pl, ol in g.triples((None, None, BNode(n))):
                    sl = str(sl).split('#')[-1]
                    pl = str(pl).split('#')[-1]
                    ol = str(ol).split('#')[-1]

                    ont[sl][pl].remove(n)
                    ont[sl].setdefault('qualifiedCardinality', set()).add((prop, ql, r))

                removed.add(n)
                solved.add(n)

            elif 'hasValue' in ont[n]:
                prop = singleton(ont[n]['onProperty'])
                r = singleton(ont[n]['hasValue'])
                for sl, pl, ol in g.triples((None, None, BNode(n))):
                    sl = str(sl).split('#')[-1]
                    pl = str(pl).split('#')[-1]
                    ol = str(ol).split('#')[-1]
                    if 'first' in ont[sl]:

                        sl = list_head(sl, g, ont)
                        if sl in removed:
                            sl = nc[sl]
                        ont[sl].setdefault('hasValue', set()).add((prop, r))

                    else:
                        ont[sl][pl].remove(n)
                        ont[sl].setdefault('hasValue', set()).add((prop, r))

                removed.add(n)
                solved.add(n)
            elif 'members' in ont[n]:
                new_name = 'Members' + '_'.join(list(ont[n]['members']))
                ont[new_name] = ont[n]
                nc[n] = new_name
                for sl, pl, ol in g.triples((None, None, BNode(n))):
                    sl = str(sl).split('#')[-1]
                    pl = str(pl).split('#')[-1]
                    ol = str(ol).split('#')[-1]

                    ont[sl][pl].add(new_name)
                    ont[sl][pl].remove(n)

                removed.add(n)
                solved.add(n)
                solved.add(new_name)

    for r in removed:
        del ont[r]

    for e in ont:

        prs = list(ont[e].keys())

        for p in prs:
            if len(ont[e][p]) <= 0:
                del ont[e][p]

        if 'subClassOf' in ont[e]:

            for sp in ont[e]['subClassOf']:
                if sp == 'Thing':
                    continue
                ont[sp].setdefault('superClassOf', set()).add(e)

        elif 'inverseOf' in ont[e]:
            inv = singleton(ont[e]['inverseOf'])
            ont[inv].setdefault('inverseOf', set()).add(e)
            ont[e]['type'].add('InverseProperty')
            ont[inv]['type'].add('InverseProperty')

        elif any(map(lambda x: 'Property' in x, ont[e]['type'])):
            if 'subPropertyOf' in ont[e]:
                sp = singleton(ont[e]['subPropertyOf'])
                ont[sp].setdefault('superPropertyOf', set()).add(e)

            if 'domain' in ont[e] and 'range' in ont[e]:
                dm = singleton(ont[e]['domain'])
                rg = singleton(ont[e]['range'])
                if dm in ont:
                    ont[dm].setdefault('out', set()).add((e, rg))
                if rg in ont:
                    ont[rg].setdefault('in', set()).add((dm, e))

                if dm == rg:
                    ont[e]['type'].add('SymmetricProperty')
            else:
                ont[e]['type'].add('AbstractProperty')

    return ont


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


def prop_dir(p):
    if p in ['in', 'subPropertyOf', 'subClassOf']:
        return -1
    else:
        print(p)
        return 1
