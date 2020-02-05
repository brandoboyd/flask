#! /usr/bin/python
# -*- coding: utf-8 -*-
"""
UI for Channels

"""
from flask import (jsonify, request, abort)

from ..app import app
from ..utils.decorators import login_required
from ..db.event_log import EventLog
from ..utils.views      import get_paging_params
import json

ModelCls = EventLog


def _user_to_ui_select(user):
    return {"id": str(user.id),
            "text": user.email}

def _params_from_request(request_data, *allowed_params):
    valid_params = {}
    for param in allowed_params:
        valid_params[param] = request_data.get(param)
    return valid_params


@app.route('/events/json',methods=['GET'])
@login_required()
def list_events(user):
    allowed_params = ('offset', 'limit',  'id','filter')
    valid_params = _params_from_request(request.args, *allowed_params)

    item_id = valid_params.pop('id', None)
    if item_id:
        try:
            #print "id:%s"%item_id
            resp = _get_event(user,item_id) 
        except  Exception, e:
            app.logger.error(e)
            return abort(500)
    else:
        try:
            resp = _get_events(user,**valid_params)
        except Exception, e:
            app.logger.error(e)
            return abort(500)
    return jsonify(resp)

def _get_events(user, **kw):
    #print "%s"%kw['limit']
    paging_params = get_paging_params(kw)
    kw.update(paging_params)
    filtr = _make_filter(kw['filter'])
    items = ModelCls.objects.find_by_user(user,**filtr).sort(**{'id': -1}).skip(kw['offset']).limit(kw['limit'])

    return dict(ok=True,
        size=len(items),
        list=[_to_ui(x,user) for x in items],
        **paging_params)


def _make_filter(filtr):
    result = {}
    filtr = json.loads(filtr) 
    name = filtr.get('title','')
    if len(name) > 0:
        result['name'] = {"$regex":".*%s.*"%filtr['title'],"$options":"i"}
    return result


def _get_event(user,id):
    item = ModelCls.objects.find_by_user(user,id=id)
    return {'ok':True,
            'item':_to_ui(item[0],user)}

def _to_ui(item,user=None):
    return {
    'title':item.name,
    'id'   :   str(item.id),
    'time' :(item.timestamp*1000),
    'user' :item.user,
    'note' :item.note,
    }
