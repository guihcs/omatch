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



class Ontology:

    def __init__(self, g):
        self.objs = dict()
        self.subj = dict()
        for s, p, o in g:

            sl = str(s).split('#')[-1]
            pl = str(p).split('#')[-1]
            ol = str(o).split('#')[-1]

            self.subj.setdefault(sl, dict()).setdefault(pl, set()).add(ol)
            self.objs.setdefault(ol, set()).add((sl, pl))

            if type(s) is BNode:
                self.subj[sl].setdefault('type', set()).add('BNode')


    def __iter__(self):
        return iter(self.subj)

    def __len__(self):
        return len(self.subj)

    def __getitem__(self, item):
        return self.subj[item]

    def __setitem__(self, key, value):
        self.subj[key] = value


    def __delitem__(self, key):
        self.subj.pop(key, None)
        self.objs.pop(key, None)

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


def list_head(start, ont):

    while True:

        start = singleton(ont.objs[start])[0]

        if 'first' not in ont[start]:
            break

    return start


def get_parents(v, g):
    return list(map(lambda x: (str(x[0]).split('#')[-1], str(x[1]).split('#')[-1]), g.triples((None, None, BNode(v)))))


def detach_node(n, ont):

    pass


def rename_node(o, n, ont):
    ont[n] = ont[o]

    if o in ont.objs:
        ont.objs[n] = ont.objs[o]

        for e, p in ont.objs[n]:
            ont[e][p].remove(o)
            ont[e][p].add(n)

    del ont[o]


def load_g(g):
    ont = Ontology(g)

    q = list(ont)
    solved = set()
    #
    while len(q) > 0:
        n = q.pop()
        if 'type' not in ont[n]:
            ont[n]['type'] = {'Misc'}

        if ref_BNode(n, ont, ignore=solved):
            q.insert(0, n)
            # print_node(n, ont)
            pass
        else:

            if 'Restriction' in ont[n]['type'] and 'allValuesFrom' in ont[n]:
                new_name = 'Only_' + singleton(ont[n]['onProperty']) + '_' + singleton(ont[n]['allValuesFrom'])
                rename_node(n, new_name, ont)
                solved.add(new_name)

            elif 'Restriction' in ont[n]['type'] and 'someValuesFrom' in ont[n]:
                new_name = 'At_least_one_' + singleton(ont[n]['onProperty']) + '_' + singleton(ont[n]['someValuesFrom'])
                rename_node(n, new_name, ont)
                solved.add(new_name)

            elif 'Restriction' in ont[n]['type'] and 'hasValue' in ont[n]:
                new_name = singleton(ont[n]['onProperty']) + '_has_value_' + singleton(ont[n]['hasValue'])
                rename_node(n, new_name, ont)
                solved.add(new_name)
            elif 'Restriction' in ont[n]['type'] and 'minCardinality' in ont[n]:
                new_name = singleton(ont[n]['onProperty']) + '_minCardinality_' + singleton(ont[n]['minCardinality'])
                rename_node(n, new_name, ont)
                solved.add(new_name)
            elif 'Restriction' in ont[n]['type'] and 'cardinality' in ont[n]:
                new_name = singleton(ont[n]['onProperty']) + '_cardinality_' + singleton(ont[n]['cardinality'])
                rename_node(n, new_name, ont)
                solved.add(new_name)
            elif 'Restriction' in ont[n]['type'] and 'maxCardinality' in ont[n]:
                new_name = singleton(ont[n]['onProperty']) + '_maxCardinality_' + singleton(ont[n]['maxCardinality'])
                rename_node(n, new_name, ont)
                solved.add(new_name)
            elif 'Restriction' in ont[n]['type'] and 'qualifiedCardinality' in ont[n]:
                dt = singleton(set(ont[n]).difference({'type', 'onProperty', 'qualifiedCardinality'}))
                new_name = singleton(ont[n]['onProperty']) + '_qualified_Cardinality_' + singleton(ont[n]['qualifiedCardinality']) + '_' + dt + '_' + singleton(ont[n][dt])
                rename_node(n, new_name, ont)
                solved.add(new_name)
            elif 'first' in ont[n]:
                v = ont[n]['first']
                t = ont[n]['rest']
                if len(ont.objs[n]) > 1:
                    print(colored(str(len(ont.objs[n])), 'red'))
                parent, w = singleton(ont.objs[n])

                if w == 'rest':
                    for qv in v:
                        if (n, 'first') in ont.objs[qv]:
                            ont.objs[qv].remove((n, 'first'))

                        ont.objs[qv].add((parent, 'first'))

                    del ont[n]

                    ont[parent]['first'].update(v)
                    ont[parent]['rest'] = t

                else:
                    for qv in v:
                        if (n, 'first') in ont.objs[qv]:
                            ont.objs[qv].remove((n, 'first'))
                        ont.objs[qv].add((parent, w))

                    del ont[n]
                    ont[parent][w].remove(n)
                    ont[parent][w].update(v)

            elif 'oneOf' in ont[n]:
                new_name = 'One_of_' + '_'.join(ont[n]['oneOf'])
                rename_node(n, new_name, ont)
                solved.add(new_name)
            elif 'unionOf' in ont[n]:
                new_name = 'Union_of_' + '_'.join(ont[n]['unionOf'])
                rename_node(n, new_name, ont)
                solved.add(new_name)
            elif 'complementOf' in ont[n]:
                new_name = 'Complement_of_' + '_'.join(ont[n]['complementOf'])
                rename_node(n, new_name, ont)
                solved.add(new_name)
            elif 'intersectionOf' in ont[n]:
                new_name = 'Intersection_of_' + '_'.join(ont[n]['intersectionOf'])
                rename_node(n, new_name, ont)
                solved.add(new_name)
            elif 'distinctMembers' in ont[n]:
                new_name = 'Distinct_members_' + '_'.join(ont[n]['distinctMembers'])
                rename_node(n, new_name, ont)
                solved.add(new_name)
            elif 'members' in ont[n]:
                new_name = 'Members' + '_'.join(ont[n]['members'])
                rename_node(n, new_name, ont)
                solved.add(new_name)
            elif 'BNode' not in ont[n]['type']:
                continue



    return ont


def parse_restriction(n, pr, ont):
    prop = singleton(ont[n]['onProperty'])
    r = singleton(ont[n][pr])
    sl = list_head(n, ont)
    ont[sl].setdefault(pr, set()).add((prop, r))
    for s, p in ont.objs[n]:

        if 'first' in ont[s]:

            for fs, fp in ont.objs[s]:
                if 'first' in ont[fs]:
                    ont[fs]['rest'] = ont[s]['rest']
                else:
                    ont[fs][fp].remove(s)


        else:
            ont[s][p].remove(n)

    del ont[n]

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
