import os

from rdflib import Graph
from os import walk
import xml.etree.ElementTree as ET
import re
import pandas as pd
import numpy as np

import multiprocessing as mp


def is_notebook():
    try:
        from IPython import get_ipython

        if "IPKernelApp" not in get_ipython().config:  # pragma: no cover
            raise ImportError("console")
            return False
        if "VSCODE_PID" in os.environ:  # pragma: no cover
            raise ImportError("vscode")
            return False
    except:
        return False
    else:  # pragma: no cover
        return True


if is_notebook():
    from tqdm.notebook import tqdm
else:
    from tqdm import tqdm


def files(base):
    for p, d, f in walk(base):
        for fl in f:
            yield f'{p}/{fl}'


def namespace(graph):
    for p, n in graph.namespaces():
        if not p:
            return n

    raise Exception('Namespace not found')


def ents(path):
    g = Graph()

    g.parse(path)

    e = set()
    nm = namespace(g)
    for s, p, o in g:
        if str(s).startswith(nm):
            e.add(s)
        if str(p).startswith(nm):
            e.add(p)
        if str(o).startswith(nm):
            e.add(o)

    return e, g


def aligns(path):
    tree = ET.parse(path)
    root = tree.getroot()

    for c in root[0]:
        if c.tag.endswith('map'):
            alc = []
            for cm in c[0]:
                if re.search(r'entity\d$', cm.tag):
                    alc.append(cm.attrib['{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource'])
            if len(alc) > 0:
                yield tuple(alc)


def onts(base, ref):
    o = files(base)
    als = files(ref)
    fd = dict()

    for f in o:
        fn = f.split('/')[-1].split('.')[0].lower()
        fd[fn] = f

    for f in als:
        f1, f2 = f.split('/')[-1].split('.')[0].lower().split('-')
        yield f, fd[f1], fd[f2]


def sim_tables(en1, en2, m):
    res = []
    for s in m:
        sm = {}
        for e1 in en1:
            for e2 in en2:
                sm[e1, e2] = s(e1, e2)

        vl = []
        for e1 in en1:
            l = []
            for e2 in en2:
                l.append(sm[e1, e2])

            vl.append(l)

        vl = np.array(vl)
        res.append(vl)
    return res


def confusion_matrix(ta, fal):
    cfm = np.zeros((2, 2))

    for e1, e2, s in fal:
        l = str(e1), str(e2)
        v2 = 1 if l in ta else 0

        cfm[s, v2] += 1

    cfm[0, 1] += len(ta) - cfm[1, 1]

    return cfm


def metrics(cfm):
    p = cfm[1, 1] + cfm[1, 0]
    precision = cfm[1, 1] / p if p != 0 else 0
    r = cfm[1, 1] + cfm[0, 1]
    recall = cfm[1, 1] / r if r != 0 else 0
    fr = precision + recall
    f = 2 * (precision * recall) / fr if fr != 0 else 0
    return precision, recall, f


def print_result(result):
    print(result)
    print(result.drop('name', axis=1).mean())


class Matcher:

    def __call__(self, *args, **kwargs):
        e1 = args[0]
        e2 = args[1]
        return self.sim(e1, e2)

    def init(self, source, target):
        pass

    def sim(self, e1, e2):
        pass


class Joiner:

    def __call__(self, *args, **kwargs):
        se = args[0]
        te = args[1]
        vl = args[2]
        return self.join(se, te, vl)

    def init(self, source, target):
        pass

    def join(self, se, te, tables):
        pass


class Runner:

    def __init__(self, base, ref, matchers, joiner):
        self.base = base
        self.ref = ref
        self.ontologies = list(onts(base, ref))
        self.matchers = matchers
        self.joiner = joiner

    def run(self, workers=2, parallel=True, context=None):

        if parallel:

            if context is not None:
                c = mp.get_context(context)
                print(c)
            else:
                c = mp
            with c.Pool(workers) as p:
                data = list(tqdm(p.imap(self.match, self.ontologies), total=len(self.ontologies)))

        else:
            data = list(tqdm(map(self.match, self.ontologies), total=len(self.ontologies)))

        rpd = pd.DataFrame(data, columns=['name', 'precision', 'recall', 'f1'])

        return rpd

    def init(self, g1, g2):
        self.joiner.init(g1, g2)
        for matcher in self.matchers:
            matcher.init(g1, g2)

    def match(self, o):
        ref = o[0]
        o1 = o[1]
        o2 = o[2]
        en1, g1 = ents(o1)
        en2, g2 = ents(o2)

        en1 = list(en1)
        en2 = list(en2)

        self.init(g1, g2)

        vl = sim_tables(en1, en2, self.matchers)

        fal = self.joiner(en1, en2, vl)

        ta = set(aligns(ref))

        cfm = confusion_matrix(ta, fal)
        precision, recall, f = metrics(cfm)

        aln = ref.split('/')[-1]

        return [aln, precision, recall, f]
