from tqdm.auto import tqdm
from collections import Counter
from nltk import word_tokenize
import json
from om.ont import tokenize
import itertools
import torch
import math
import multiprocessing_on_dill as mp


def filter_sub_word(sub):
    so = sorted(list(sub.items()), key=lambda x: len(x[0]), reverse=True)

    res = []

    for i in tqdm(range(len(so))):
        s, c = so[i]

        if c < 100:
            continue

        for j in range(i + 1, len(so)):
            sw, sc = so[j]
            if s.startswith(sw):
                so[j] = (sw, sc - c)

        res.append(so[i])

    return set(map(lambda x: x[0], res))


def gen_subs(w, seq):
    res = set()
    for i in seq:
        for j in range(i, len(w)):
            p = '##' if i > 0 else ''
            res.add(p + w[i:j + 1])

    return res


def gen_ids(w, rv):
    li = 0
    out = [li]

    while li != len(w):

        for i in range(len(w), li, -1):
            p = '##' if li > 0 else ''
            if p + w[li:i] in rv:
                li = i
                if i < len(w):
                    out.append(i)
                break
        else:
            break
    return out


def build_vocab(sents, language, ron=2):
    counter = Counter()
    for t in tqdm(sents, leave=False):
        counter.update(word_tokenize(t, language=language))

    progress = tqdm(total=ron * len(counter.items()))
    for qw in range(ron):

        subw = Counter()

        for w, c in counter.items():

            if qw > 0 and w not in rv:
                ids = gen_ids(w, rv)
            else:
                ids = range(0, len(w))

            subs = gen_subs(w, ids)
            for s in subs:
                subw[s] += c

            progress.update(1)
        rv = filter_sub_word(subw)

    progress.close()
    return rv


def stokenize(w, rv):
    if w in rv:
        return [w]

    li = 0
    out = []

    while li != len(w):

        for i in range(len(w), li, -1):
            p = '##' if li > 0 else ''
            if p + w[li:i] in rv:
                out.append(p + w[li:i])
                li = i
                break
        else:
            out = ['[UNK]']
            break

    return out


def get_max_len(s):
    if len(s) <= 0:
        return [0]

    if type(s[0]) is not list:
        return [len(s)]

    max_ml = None
    for q in s:
        if max_ml is None:
            max_ml = get_max_len(q)
            continue

        ml = get_max_len(q)

        for i, (q1, q2) in enumerate(zip(max_ml, ml)):
            max_ml[i] = max(q1, q2)

    return [len(s)] + max_ml


class Tokenizer:

    def __init__(self):
        self.vocabulary = None
        self.wi = dict()
        self.iw = dict()
        pass

    def build_vocab(self, sents, lang='english', ron=2, reserved=None):
        vocabulary = build_vocab(sents, 'english', ron=3)

        self.load_vocab(vocabulary, reserved)

        return self

    def load_vocab(self, vocab, reserved=None):
        self.vocabulary = vocab

        if reserved is None:
            reserved = []

        for i, w in enumerate(reserved + list(self.vocabulary)):
            self.wi[w] = i
            self.iw[i] = w

    def vocab_size(self):
        return len(self.wi)

    def save(self, path):
        with open(path, 'w') as f:
            f.write(json.dumps(self.wi))

    def load(self, path):
        with open(path, 'r') as f:
            self.wi = json.loads(f.read())

        for w, i in self.wi.items():
            self.iw[i] = w

        self.vocabulary = set(self.wi.keys())

    def tokenize(self, s):
        ns = [tokenize(q) for q in s]
        sec = [stokenize(x.lower(), self.vocabulary) for x in itertools.chain(*ns)]
        return list(itertools.chain(*sec))

    def batch_tokenize(self, g):

        return list(map(self.tokenize, g))

    def batch_encode(self, s, token_max_len=-1):

        return torch.IntTensor(self.raw_batch_encode(s, token_max_len))

    def raw_batch_encode(self, s, token_max_len=-1):

        max_len = get_max_len(s)
        if token_max_len != -1:
            max_len[-1] = token_max_len

        padded_seq = self.pad_seq(s, 0, max_len)

        return padded_seq

    def pad_seq(self, s, l, ml):

        if type(s[0]) is not list:
            if len(s) > ml[l]:
                s = s[:ml[l]]
            return list(map(lambda x: self.wi[x] if x in self.wi else 1, s)) + [0] * (ml[l] - len(s))

        ns = []
        for q in s:
            if len(q) <= 0:
                q = ['[UNK]']
            ns.append(self.pad_seq(q, l + 1, ml))

        lp = 0

        for w in reversed(ml[l + 1:]):
            lp = [lp] * w

        return ns + [lp] * (ml[l] - len(ns))


def part(seq, pl):
    for i in range(0, len(seq), pl):
        yield seq[i: i + pl]


def count(sents):
    counter = Counter()

    for t in sents:
        counter.update(word_tokenize(t, language='english'))

    return counter


def reduce(maps):
    counter = Counter()

    for c in maps:
        counter += c

    return counter


class Node:

    def __init__(self, value):
        self.value = value
        self.child = {}
        self.lens = []

    def __repr__(self):
        return repr(self.lens) + ' ' + repr(self.child)


def find_path(root, value):
    for l in root.lens:
        vk = value[:l]
        if vk in root.child:
            rp = find_path(root.child[vk], value)
            return rp + [vk]

    return []


def add_value(root, value):
    if len(root.child) <= 0:
        root.child[value] = Node(value)
        root.lens.append(len(value))
        return

    for l in root.lens:
        vk = value[:l]
        if vk in root.child:
            add_value(root.child[vk], value)
            return

    root.child[value] = Node(value)

    if root.lens[-1] < len(value):
        root.lens.append(len(value))


def filter_part(sop, subw):
    root = Node('')

    for v in tqdm(list(reversed(sop))):
        add_value(root, v)

    for s in sop:

        if subw[s] < 100:
            continue

        for p in find_path(root, s)[1:]:
            subw[p] -= subw[s]

    res = set()

    for k, c in subw.items():
        if c < 100:
            continue
        res.add(k)

    return res


def count_subs(items, qw, rv):
    subw = Counter()

    for w, c in items:

        if qw > 0 and w not in rv:
            ids = gen_ids(w, rv)
        else:
            ids = range(0, len(w))

        subs = gen_subs(w, ids)
        for s in subs:
            subw[s] += 1

    return subw


def parallel_build_vocab(sents, language, ron=2, chunk_size=50_000, workers=2):


    with mp.Pool(workers) as p:
        maps = list(tqdm(p.imap(count, part(sents, chunk_size)), total=math.ceil(len(sents) / chunk_size)))

    with mp.Pool(workers) as p:
        maps = list(tqdm(p.imap(reduce, part(maps, workers)), total=math.ceil(len(maps) / workers)))

    counter = reduce(maps)
    rv = None

    for qw in tqdm(range(ron)):
        with mp.Pool(workers) as p:
            subs = list(tqdm(p.imap(lambda x: count_subs(x, qw, rv), part(list(counter.items()), chunk_size)),
                             total=math.ceil(len(counter.items()) / chunk_size)))

        subw = reduce(tqdm(subs))

        so = sorted(list(subw.items()), key=lambda x: len(x[0]), reverse=True)

        rv = filter_part(so, subw)

    return rv
