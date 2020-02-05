#!/bin/sh

./datasift_bot.py                                 \
    --username=super_user@solariat.com            \
    --ds_api_key=7922bc2db3dcab55c7869c545f9701cd \
    --ds_login=mcgannc                            \
    --concurrency=4                               \
    --password=password                     \
    --url=http://tango.solariat.dev:5000   \
    --post_creator=http_post_api            \
    --dumpfile=/tmp/datasift.dump
