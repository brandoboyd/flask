import json


def filestream(languages=('en',), sample_count=10):
    import os
    import solariat_bottle
    filename = os.path.join(
        os.path.dirname(solariat_bottle.daemons.twitter.stream.__file__),
        'sample.json')

    with open(filename) as source:
        n = sample_count
        while n:
            data = source.readline()
            if not data:
                source.seek(0)
                continue

            if not languages or json.loads(data).get('lang') in languages:
                yield data
                n -= 1
