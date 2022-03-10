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
            print_node(q, ont, cl=cl+2, ml=ml)

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


def ref_BNode(n, ont):
    for p in ont[n]:
        for v in ont[n][p]:
            if v not in ont:
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


def load_g(g):
    ont = g2dict(g)

    cp = dict()
    mp = list(ont.keys())
    rl = dict()
    i = 0
    while len(mp) > 0:

        if i > 10000:
            for m in mp:
                print_node(m, ont)
            raise Exception('Max Iterations')
        n = mp.pop(0)
        if 'type' not in ont[n]:
            ont[n]['type'] = {'Misc'}

        if not ref_BNode(n, ont):
            if 'BNode' not in ont[n]['type']:
                cp[n] = ont[n]
                continue
            elif 'Restriction' in ont[n]['type']:

                if 'onProperty' in ont[n]:
                    p = singleton(ont[n]['onProperty'])


                    if p in cp:

                        for tp in set(ont[n].keys()).difference({'type', 'onProperty'}):
                            cp[p].setdefault(tp, set()).update(ont[n][tp])



                    else:
                        for tp in set(ont[n].keys()).difference({'type', 'onProperty'}):
                            ont[p].setdefault(tp, set()).update(ont[n][tp])

                    for s, rp, o in g.triples((None, None, BNode(n))):
                        s = str(s).split('#')[-1]
                        rp = str(rp).split('#')[-1]
                        o = str(o).split('#')[-1]


                        if s in cp:
                            cp[s].setdefault('restriction', set()).add(p)
                            cp[s][rp].remove(n)
                            if rp == 'complementOf':
                                ont[s][rp].add(p)
                            else:
                                if len(cp[s][rp]) <= 0:
                                    del cp[s][rp]

                        else:
                            ont[s].setdefault('restriction', set()).add(p)
                            ont[s][rp].remove(n)
                            if rp == 'complementOf':
                                ont[s][rp].add(p)


                            if len(ont[s][rp]) <= 0:
                                del ont[s][rp]

                    continue

            elif 'complementOf' in ont[n]:
                comp = singleton(ont[n]['complementOf'])
                new_name = 'ComplementOf' + comp
                cp[new_name] = ont[n]

                for s, p, o in g.triples((None, None, BNode(n))):
                    s = str(s).split('#')[-1]
                    p = str(p).split('#')[-1]
                    o = str(o).split('#')[-1]

                    ont[s][p].add(new_name)
                    ont[s][p].remove(n)

                continue

            else:
                rl[n] = ont[n]
                continue

        else:
            if len(set(ont[n]).intersection({'unionOf', 'oneOf', 'intersectionOf', 'distinctMembers', 'members'})) > 0 :
                qwe = singleton(set(ont[n]).intersection({'unionOf', 'oneOf', 'intersectionOf', 'distinctMembers', 'members'}))
                v = singleton(ont[n][qwe])
                if v not in rl:
                    values = set()
                    rest = v

                    while rest != 'nil':
                        if rest in mp:
                            mp.remove(rest)

                        if 'first' not in ont[rest]:
                            values.update(ont[rest]['restriction'])
                        else:
                            values.update(ont[rest]['first'])

                        rest = singleton(ont[rest]['rest'])

                    ont[v]['first'] = values
                    rl[v] = ont[v]

                ont[n][qwe] = rl[v]['first']
                new_name = qwe[0].upper() + qwe[1:] + 'And'.join(list(ont[n][qwe]))
                cp[new_name] = ont[n]
                for s, p, o in g.triples((None, None, BNode(n))):
                    s = str(s).split('#')[-1]
                    p = str(p).split('#')[-1]
                    o = str(o).split('#')[-1]


                    ont[s][p].add(new_name)
                    ont[s][p].remove(n)
                continue





        mp.append(n)
        i += 1


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
