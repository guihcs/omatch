from om.match import Step


def match_format(dataset, e1, e2, s):

    return dataset.n1 + e1, dataset.n2 + e2, s



class Cross(Step):

    def forward(self, dataset):

        ents = []

        for e1 in dataset.ont1:
            if 'BNode' in dataset.ont1[e1]['type']:
                continue
            for e2 in dataset.ont2:
                if 'BNode' in dataset.ont2[e2]['type']:
                    continue

                if len(dataset.ont1[e1]['type'].intersection(dataset.ont2[e2]['type'])) < 1:
                    continue

                ents.append((e1, e2))

        return ents