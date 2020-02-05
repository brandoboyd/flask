# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0

from solariat_bottle.workers import io_pool


@io_pool.task
def log_event(event):
    "Store event into DB"
    event.log()

