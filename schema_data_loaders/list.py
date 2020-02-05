class ListDataLoader(object):
    '''Used as util, supposed to keep homogeneous data'''

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def total(self):
        return len(self.raw_data)

    def load_data(self):
        for item in self.raw_data:
            yield item
    