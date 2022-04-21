import re
from termcolor import colored
from rdflib import BNode, Graph
from rdflib import Literal
from rdflib import URIRef
from rdflib.namespace import RDF, RDFS, OWL
import random
import copy


def pc(n, g):
    color_map = {
        'owl': 'blue',
        'rdf': 'red',
        'rdfs': 'magenta',
        'xsd': 'green',
        '_': 'cyan'
    }
    n = n.n3(g.namespace_manager)
    s = re.sub(r'.+\^\^', '', n).split(':')
    if s[0] in color_map:
        return colored(n, color_map[s[0]])

    return n


def pt(s, p, o, g):
    print(pc(s, g), pc(p, g), pc(o, g))


def rename_ent(old, new, g):
    ot = []
    nt = []

    for s, p, o in g.triples((old, None, None)):
        ot.append((s, p, o))
        nt.append((new, p, o))

    for s, p, o in g.triples((None, None, old)):
        ot.append((s, p, o))
        nt.append((s, p, new))

    for t in ot:
        g.remove(t)

    for t in nt:
        g.add(t)


def remove_ent(ent, g):
    rt = []

    for t in g.triples((ent, None, None)):
        rt.append(t)

    for t in g.triples((None, None, ent)):
        rt.append(t)

    for t in rt:
        g.remove(t)


def remove_bn(g):
    tp = []
    lt = set()

    for s, p, o in g.triples((None, None, None)):
        if (o, RDF.first, None) in g:
            if p != RDF.rest:
                lt.add(p)
            vals = []
            start = o
            while start != RDF.nil:
                vals.append(g.value(start, RDF.first))
                start = g.value(start, RDF.rest)

            tp.append(((s, p, o), vals))

    for (s, p, o), vals in tp:
        for v in vals:
            g.add((s, p, v))
        g.remove((s, p, o))

    g.remove((None, RDF.first, None))
    g.remove((None, RDF.rest, None))

    pref, uri = list(filter(lambda x: x[0] == '', g.namespaces()))[0]

    rnm = []

    for s in g.subjects(RDF.type, OWL.Restriction):
        value = g.value(s, OWL.onProperty)
        prefix, label = value.n3(g.namespace_manager).split(':')
        rn = URIRef(uri + 'Restriction_on_' + label)
        rnm.append((s, rn))

    for s, rn in rnm:
        rename_ent(s, rn, g)

    rnm = []
    for s in g.subjects(OWL.complementOf, None):
        val = g.value(s, OWL.complementOf).n3(g.namespace_manager).split(':')[1]
        rn = URIRef(uri + 'complementOf_' + val)
        rnm.append((s, rn))

    for s, rn in rnm:
        rename_ent(s, rn, g)

    rm = dict()

    for jp in lt:
        for s in g.subjects(jp, None):
            rm[s] = jp

    flt = list(rm)

    while len(flt) > 0:
        k = flt.pop()
        objs = list(g.objects(k, rm[k]))
        if any(map(lambda x: type(x) is BNode, objs)):
            flt.insert(0, k)
        else:
            jn = []
            for o in objs:

                if type(o) is Literal:
                    name = o.value.replace(' ', '_')

                else:
                    name = o.n3(g.namespace_manager).split(':')[1]

                jn.append(name)

            nn = uri + rm[k].n3(g.namespace_manager).split(':')[1] + '_' + '_'.join(jn)
            rename_ent(k, URIRef(nn), g)


def get_char_class(c):
    if len(c) <= 0:
        return -1
    if c.isalpha():
        return 0
    if c.isnumeric():
        return 1
    if c.isspace():
        return 2
    if not c.isalnum():
        return 3


def split_sent(e):
    if len(e) <= 1:
        return [(e, get_char_class(e))]
    split = []
    lc = get_char_class(e[0])
    sb = e[0]
    for c in list(e)[1:]:
        cc = get_char_class(c)
        if cc == lc:
            sb += c
        else:
            split.append((sb, lc))
            sb = c
        lc = cc

    split.append((sb, lc))
    return split


def get_lc(c):
    if c.islower():
        return 0
    if c.isupper():
        return 1
    return 2


def split_w(w):
    split = []
    lc = -1
    sb = ''
    for c in list(w):
        cc = get_lc(c)

        if cc == 1 and lc != 1 and lc != -1:
            split.append(sb)
            sb = ''

        sb += c
        lc = cc

    split.append(sb)

    return split


def split_entity(e):
    s = split_sent(e)

    split = []

    for w, t in s:
        if t == 0:
            split += split_w(w)
        elif t == 1:
            split.append(w)

    return split


def get_namespace(g):
    for p, uri in g.namespaces():
        if not p:
            return uri
    return ''


def remove_word(u, g, uri):
    name = u.n3(g.namespace_manager).split(':')[1]
    split = split_entity(name)
    ni = list(range(0, len(split)))

    while len(ni) > 0:
        i = random.randint(0, len(ni) - 1)
        si = ni.pop(i)
        cs = copy.copy(split)
        cs.pop(si)
        nn = uri + '_'.join(cs)

        if (nn, None, None) not in g:
            rename_ent(u, nn, g)
            return nn
    return u


def inject_word(u, g, vocab, mt=1):
    fv = list(vocab)
    for _ in range(mt):
        v = random.choice(fv)
        nn = u + '_' + v
        if (nn, None, None) not in g:
            rename_ent(u, nn, g)
            return nn
    return u


def merge(u1, u2, g, uri):
    if ':' not in u1.n3(g.namespace_manager) or ':' not in u2.n3(g.namespace_manager):
        return u1
    n1 = u1.n3(g.namespace_manager).split(':')[1]
    n2 = u2.n3(g.namespace_manager).split(':')[1]
    nn = uri + n1 + '_' + n2
    if (nn, None, None) in g:
        return None
    rename_ent(u1, nn, g)
    rename_ent(u2, nn, g)
    for s, p, o in g.triples((nn, None, nn)):
        g.remove((s, p, o))
    return nn


def split(u, g, uri):
    name = u.n3(g.namespace_manager).split(':')[1]
    split = split_entity(name)
    if len(split) <= 1:
        return u, u

    i = random.randint(1, len(split) - 1)

    nn1 = uri + '_'.join(split[0:i])
    nn2 = uri + '_'.join(split[i:])
    if (nn1, None, None) in g or (nn2, None, None) in g:
        return u, u

    st = list(g.triples((u, None, None)))
    ot = list(g.triples((None, None, u)))

    remove_ent(u, g)

    if len(st) <= 1:
        for s, p, o in st:
            g.add((nn1, p, o))
    else:
        i = random.randint(1, len(st) - 1)
        for _, p, o in st[:i]:
            g.add((nn1, p, o))

        for _, p, o in st[i:]:
            g.add((nn2, p, o))

    if len(ot) <= 1:
        for s, p, o in st:
            g.add((s, p, nn1))
    else:
        i = random.randint(1, len(ot) - 1)
        for s, p, _ in ot[:i]:
            g.add((s, p, nn1))

        for s, p, _ in ot[i:]:
            g.add((s, p, nn2))

    r = random.random()

    if r < 0.33:
        g.add((nn1, RDFS.subClassOf, nn2))
    elif r < 0.66:
        g.add((nn2, RDFS.subClassOf, nn1))
    else:
        g.add((nn1, OWL.equivalentClass, nn2))

    return nn1, nn2


def swap(u1, u2, g, uri):
    tmp = uri + 'tmp' + str(random.randint(100000000, 10000000000000))

    while (tmp, None, None) in g:
        tmp = uri + 'tmp' + str(random.randint(100000000, 10000000000000))

    rename_ent(u1, tmp, g)
    rename_ent(u2, u1, g)
    rename_ent(tmp, u2, g)


def change_triple(u, g):
    triples = list(g.triples((u, None, None)))
    if len(triples) < 2:
        return
    rc = random.choice(triples)
    st = list(g.triples((None, rc[1], None)))
    rt = random.choice(st)

    g.remove(rc)
    g.add((rc[0], rc[1], rt[2]))


def add_random_triple(g):
    rs = list(g.triples((None, None, None)))

    t1 = random.choice(rs)
    t2 = random.choice(rs)
    t3 = random.choice(rs)

    g.add((t1[0], t2[1], t3[2]))


def noisy_copy(g, tl=None):
    if tl is None:
        tl = [0.15]

    vocab = set()
    for s, p, o in g:
        vocab.update(set(split_entity(s)))
        vocab.update(set(split_entity(p)))
        vocab.update(set(split_entity(o)))

    uri = get_namespace(g)
    gc = Graph()

    gc += g
    gc.namespace_manager = g.namespace_manager
    aligns = set()

    subjects = list(g.subjects())
    for s in subjects:
        aligns.add((s, s))

    for s in gc.subjects():
        if (s, s) not in aligns:
            continue
        lp = 0
        rv = random.random()
        for p in tl:
            if rv < p + lp:
                rn = random.random()
                if rn < 0.14286:
                    nn = remove_word(s, gc, uri)

                    aligns.discard((s, s))
                    aligns.add((s, nn))
                elif rn < 0.28572:
                    nn = inject_word(s, gc, vocab)

                    aligns.discard((s, s))
                    aligns.add((s, nn))
                elif rn < 0.42858:
                    rs = random.choice(subjects)
                    if ':' not in s.n3(g.namespace_manager) or ':' not in rs.n3(g.namespace_manager):
                        continue
                    aligns.discard((rs, rs))
                    nn = merge(s, rs, gc, uri)
                    aligns.discard((s, s))
                    aligns.add((s, nn))
                elif rn < 0.57144:
                    nn1, nn2 = split(s, gc, uri)
                    aligns.discard((s, s))
                    if random.random() < 0.5:
                        aligns.add((s, nn1))
                    else:
                        aligns.add((s, nn2))
                elif rn < 0.7143:
                    rs = random.choice(subjects)
                    aligns.discard((rs, rs))
                    swap(s, rs, gc, uri)
                    aligns.discard((s, s))
                    aligns.add((s, rs))
                    aligns.add((rs, s))
                elif rn < 0.85716:
                    change_triple(s, gc)
                else:
                    add_random_triple(gc)

            lp += p

    return gc, aligns


def get_n(e, g):
    v = e.n3(g.namespace_manager)
    if ':' in v:
        return v.split(':')[1]

    return None