"Functions for calculating matchable-post relevance"

from solariat_nlp import scoring


def get_post_matchable_relevance(post, matchable):
    '''
    Just a little wrapper to get the normalized relevance score
    for a post.
    '''
    return scoring.get_post_matchable_distance(post, matchable)[0]
