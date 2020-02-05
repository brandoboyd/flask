#! /usr/bin/python
# -*- coding: utf-8 -*-
""" UI for Channels """
from flask import jsonify

from solariat_bottle.app import app
from solariat_bottle.db.dashboard import Dashboard, DashboardWidget
from solariat_bottle.utils.decorators import login_required


def get_adapted_form(*args, **kw):
    from solariat_bottle.api.base import get_adapted_form
    return get_adapted_form(*args, **kw)


@app.route('/dashboard/new', methods=['POST'])
@login_required()
def create_widget(user, **settings):
    widget_data = get_adapted_form(DashboardWidget)
    dashboard_id = widget_data.get('dashboard_id')

    if dashboard_id is None:
        # if client sends null dashboard_id, use 'blank' dashboard
        dashboard = Dashboard.objects.get_or_create_blank_dashboard(user)
    else:
        dashboard = Dashboard.objects.get(dashboard_id)

    widget_data['dashboard_id'] = dashboard.id
    widget = DashboardWidget.objects.create_by_user(user=user, **widget_data)

    return jsonify(ok=True, item=widget.to_dict())


@app.route('/dashboard/list', methods=['GET'])
@login_required()
def list_widgets(user):
    widgets = [w.to_dict() for w in DashboardWidget.objects.find(user=user.id)]
    widgets.sort(key=lambda x: x['order'])
    return jsonify(ok=True, list=widgets)


@app.route('/dashboard/reorder', methods=['POST'])
@login_required()
def reorder_widgets(user):
    widget_data = get_adapted_form(DashboardWidget)
    successes = []
    errors = []
    for widget_id in widget_data:
        widget_order = widget_data[widget_id]
        try:
            widget = DashboardWidget.objects.get(widget_id)
            widget.order = int(widget_order)
            widget.save()
            successes.append({widget_id: widget_order})
        except DashboardWidget.DoesNotExist:
            errors.append({widget_id: "No widget with this id."})
        except Exception, ex:
            errors.append({widget_id: "Unhandled exception: " + str(ex)})
    if not successes:
        return jsonify(ok=False, success=successes, errors=errors)
    else:
        return jsonify(ok=True, success=successes, errors=errors)


@app.route('/dashboard/<widget_id>/update', methods=['POST'])
@login_required()
def update_widget(user, widget_id):
    try:
        widget = DashboardWidget.objects.get(widget_id)
    except DashboardWidget.DoesNotExist:
        return jsonify(ok=False, error="No widget was found for id=%s" % (widget_id,))
    new_widget_data = get_adapted_form(DashboardWidget)
    if 'title' in new_widget_data:
        widget.title = new_widget_data.pop('title')
    if 'order' in new_widget_data:
        widget.order = int(new_widget_data.pop('order'))
    widget.settings.update(new_widget_data)
    widget.save()
    return jsonify(ok=True, item=widget.to_dict())


@app.route('/dashboard/<widget_id>/remove', methods=['DELETE'])
@login_required()
def remove_widget(user, widget_id):
    try:
        widget = DashboardWidget.objects.get(widget_id)
    except DashboardWidget.DoesNotExist:
        return jsonify(ok=False, error="No widget was found for id=%s" % (widget_id,))
    widget.delete()
    return jsonify(ok=True)


@app.route('/dashboard/<widget_id>/widget', methods=['GET'])
@login_required()
def get_widget(user, widget_id):
    try:
        widget = DashboardWidget.objects.get(widget_id)
    except DashboardWidget.DoesNotExist:
        return jsonify(ok=False, error="No widget was found for id=%s" % (widget_id,))
    return jsonify(ok=True, item=widget.to_dict())
