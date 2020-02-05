# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0

from solariat_bottle.workers import io_pool

from . import nlp


logger = io_pool.logger


# --- throughput test tasks ---

@io_pool.task
def tt_process_post(post):
    intentions = nlp.extract_intentions.delay(post)  # calling a CPU task
    return io_pool.db.throughput_test.insert({
        'post'       : post,
        'intentions' : intentions
    }, w=1)

@io_pool.task
def tt_drop_test_collections():
    res = io_pool.db.throughput_test.drop()
    return res

@io_pool.task(timeout=None)
def tt_slow_task(N=15):
    "A dummy task that waits N seconds and returns N"
    io_pool.tools.sleep(N)
    return N
