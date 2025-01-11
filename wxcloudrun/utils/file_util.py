import json


def loads_json(path):
    ds = []
    with open(path, encoding='utf') as f:
        for line in f.readlines():
            d = json.loads(line)
            ds.append(d)
    return ds