from rdflib import BNode, RDF

from om.match import Step


def is_not_bn(n):
    return type(n) is not BNode


class Cross(Step):

    def forward(self, dataset):

        ents = []

        for e1 in filter(is_not_bn, set(dataset.g1.subjects())):
            for e2 in filter(is_not_bn, set(dataset.g2.subjects())):

                if len(set(dataset.g1.objects(e1, RDF.type)).intersection(dataset.g2.objects(e2, RDF.type))) < 1:
                    continue

                ents.append((e1, e2))

        return ents


class WordMap:

    def __init__(self, vocab=None):
        self.i = 0
        self.wi = dict()
        self.iw = dict()

        if vocab is not None:
            self.add_all(vocab)

    def add(self, word):
        self.wi[word] = self.i
        self.iw[self.i] = word
        self.i += 1

    def add_all(self, vocab):
        for w in vocab:
            self.add(w)

    def __getitem__(self, i):
        return self.wi[i]

    def get_w(self, i):
        return self.iw[i]

    def map(self, w):
        if w not in self.wi:
            self.add(w)
        return self.wi[w]

    def get_vocab(self):
        return set(self.wi.keys())

    def __len__(self):
        return self.i

    def __contains__(self, x):
        return x in self.wi





