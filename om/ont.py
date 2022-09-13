import re
from termcolor import colored
from rdflib import Graph
from rdflib.term import Literal, BNode, URIRef
from rdflib.namespace import RDF, RDFS, OWL
from tqdm.auto import tqdm
import random
import copy


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


def tokenize(e):
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



def get_n(e, g):

    if type(e) is BNode:
        return str(e)
    elif type(e) is URIRef:
        v = e.n3(g.namespace_manager)
        if ':' in v:
            return v.split(':')[1]
    elif type(e) is Literal:
        return str(e)

    raise Exception(f'Type {type(e)} not found.')


def get_vocab(g):
    vocab = set()
    for s, p, o in g:
        vocab.update(set(tokenize(s)))
        vocab.update(set(tokenize(p)))
        vocab.update(set(tokenize(o)))

    return vocab