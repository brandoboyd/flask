# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0

from smhasher import murmur3_x86_128


def mhash(data, n=32):
    """
    Returns an N-bit hash value of provided data (string)
    generated with the Murmur3 hashing.

    n - is a number of bits in a final mask [0..128].
        None means no masking.
    """
    if not isinstance(data, basestring):
        try:    data = str(data)
        except: data = unicode(data)

    if isinstance(data, unicode):
        data = data.encode('utf-8')

    value = murmur3_x86_128(data)

    if n is None:
        return value
    else:
        mask = (1L << n) - 1
        return value & mask

