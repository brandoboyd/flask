# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0

from solariat_bottle.workers import io_pool
from solariat.utils.lang.support import LangCode

_extract_intentions = None
_classify_content   = None

logger = io_pool.logger


# --- CPU-worker initialization ----

@io_pool.prefork  # CPU-workers will run this before forking
def warmup_nlp():
    """ Make sure all heavy caches are populated before we fork
        to benefit from the Copy-on-Write kernel optimization
    """
    logger.info("warming up NLP code")

    # import here to keep io_workers from pulling this into memory also
    from solariat_nlp import (
        extract_intentions,
        classify_content
    )
    global _extract_intentions, _classify_content
    _extract_intentions = extract_intentions
    _classify_content   = classify_content

    extract_intentions("Initializing and filling up the caches")
    extract_intentions("Processing multiple. Utterances! In one post >:)")

    logger.info('done')


# --- CPU-bound tasks ----

@io_pool.task
def extract_intentions(post, lang=LangCode.EN):
    return _extract_intentions(post, lang=lang)

@io_pool.task
def classify_content(post, lang=LangCode.EN):
    return _classify_content(post, lang=lang)
