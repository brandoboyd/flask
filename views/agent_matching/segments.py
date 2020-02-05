# from flask import jsonify, request
#
# from solariat_bottle.app import app
# from solariat_bottle.utils.decorators import login_required
#
#
# @app.route('/customer_segments', methods=['POST'])
# @login_required
# def create_customer_segment(user):
#     request_data = request.json
#
#     create_data = {}
#     required_fields = ['channel_id', 'display_name']
#     # List of names and default values if not present
#     accepted_fields = [('precondition', None), ('acceptance_rule', None), ('is_multi', False)]
#
#     for field in required_fields:
#         if field not in request_data or not request_data[field]:
#             return jsonify(ok=False, error="Missing required parameter '%s'" % field)
#         create_data[field] = request_data[field]
#
#     for field, default in accepted_fields:
#         create_data[field] = request_data.get(field, default)
#
#     instance = CustomerSegment.objects.create(**create_data)
#     return jsonify(ok=True, item=instance.to_dict())
#
#
# @app.route('/customer_segments', methods=['GET'])
# @login_required
# def list_customer_segments(user):
#     label_data = request.args
#
#     segment_id = label_data.get('segment_id', None)
#
#     if segment_id:
#         try:
#             return jsonify(ok=True, item=CustomerSegment.objects.get(segment_id).to_dict())
#         except CustomerSegment.DoesNotExist:
#             return jsonify(ok=True, error='No label with id=%s found' % segment_id)
#     elif user.account:
#         labels_list = sorted([lbl.to_dict() for lbl in
#             CustomerSegment.objects.find(account_id=user.account.id, is_multi=False)],
#             key=lambda d: d['display_name'])
#         return jsonify(ok=True, list=labels_list)
#     else:
#         return jsonify(ok=False, error="Either channel or agent_id needs to be provided.")
#
#
# @app.route('/customer_multi_segments', methods=['POST'])
# @login_required
# def create_customer_multi_segment(user):
#     request_data = request.json
#
#     create_data = {}
#     required_fields = ['segment_options', 'display_name']
#     # List of names and default values if not present
#
#     for field in required_fields:
#         if field not in request_data or not request_data[field]:
#             return jsonify(ok=False, error="Missing required parameter '%s'" % field)
#         create_data[field] = request_data[field]
#
#     create_data['account_id'] = user.account.id
#     segments_data = create_data.pop('segment_options')
#     segments = []
#     for data_entry in segments_data:
#         data_entry['is_multi'] = True
#         option = CustomerSegment.objects.create(**data_entry)
#         segments.append(option.id)
#     create_data['segment_options'] = segments
#
#     instance = CustomerMultiSegment.objects.create(**create_data)
#     return jsonify(ok=True, item=instance.to_dict())
#
#
# @app.route('/customer_multi_segments', methods=['GET'])
# @login_required
# def list_customer_multi_segments(user):
#     label_data = request.args
#
#     segment_id = label_data.get('segment_id', None)
#
#     if segment_id:
#         try:
#             return jsonify(ok=True, item=CustomerMultiSegment.objects.get(segment_id).to_dict())
#         except CustomerSegment.DoesNotExist:
#             return jsonify(ok=True, error='No label with id=%s found' % segment_id)
#     elif user.account:
#         labels_list = [lbl.to_dict() for lbl in CustomerMultiSegment.objects.find(account_id=user.account.id)]
#         return jsonify(ok=True, list=labels_list)
#     else:
#         return jsonify(ok=False, error="Either channel or agent_id needs to be provided.")
