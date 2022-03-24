import os

from rdflib import Graph
from os import walk
import xml.etree.ElementTree as ET
import re
import pandas as pd
import numpy as np

import multiprocessing

from om.ont import namespace, load_g


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




class Runner:

    def __init__(self, base, ref, matcher):
        self.base = base
        self.ref = ref
        self.ontologies = list(onts(base, ref))
        self.matcher = matcher


    def run(self, workers=2, parallel=True, context=None, mp=None, refs=None):

        if refs is not None:
            tst = list(filter(lambda x: x[0] in refs, self.ontologies))
        else:
            tst = self.ontologies

        mp = mp if mp is not None else multiprocessing
        if parallel:

            if context is not None:
                c = mp.get_context(context)
            else:
                c = mp
            with c.Pool(workers) as p:
                data = list(tqdm(p.imap(self.match, tst), total=len(tst)))

        else:
            data = list(tqdm(map(self.match, tst), total=len(tst)))

        rpd = [[] for _ in data[0]]

        for d in data:
            for i in range(len(rpd)):
                rpd[i].append(d[i])

        fr = []
        for d in rpd:
            fr.append(pd.DataFrame(d, columns=['name', 'precision', 'recall', 'f1']))

        return fr

    def match(self, o):
        ref = o[0]
        o1 = o[1]
        o2 = o[2]
        dataset = Dataset(o1, o2)

        ta = set(aligns(ref))
        fal = self.matcher(dataset)
        if fal is None:
            raise Exception('Empty result.')


        res = []

        aln = ref.split('/')[-1]

        for i in range(len(fal)):

            cfm = confusion_matrix(ta, fal[i])
            precision, recall, f = metrics(cfm)

            res.append([aln, precision, recall, f])

        return res



class Step:

    def __call__(self, *args, **kwargs):
        return self.forward(*args)


    def forward(self, *args):

        pass


    def __repr__(self):
        atrs = '\n\t'.join([x + ': ' + str(vars(self)[x]) for x in vars(self)])
        return f'{type(self).__name__}\n\t{atrs}'


class Horizontal(Step):


    def __init__(self, stack):
        self.stack = stack

    def forward(self, *args):
        return [x(*args) for x in self.stack]


class Stack(Step):

    def __init__(self, stack):
        self.stack = stack

    def forward(self, *args):
        if len(self.stack) <= 0:
            return None
        r = args

        for s in self.stack:
            r = tuple([s(*r)])

        return r[0]

class Pass(Step):

    def forward(self, *args):
        return args


class Dataset:

    def __init__(self, o1, o2):
        self.g1 = Graph()
        self.g1.parse(o1)
        self.g2 = Graph()
        self.g2.parse(o2)

        self.n1 = namespace(self.g1)
        self.n2 = namespace(self.g2)

        self.ont1 = load_g(self.g1)
        self.ont2 = load_g(self.g2)



