# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0

from solariat_nlp.utils.topics import gen_speech_act_terms


def get_topic_tuples(sa, post, channel):
    """ Returns a list of dicationaries, each containing the topic details
    """
    tuples = gen_speech_act_terms(sa, post, include_all=False, channel=channel)
    return [dict(t=t[0], l=t[3]) for t in tuples]

