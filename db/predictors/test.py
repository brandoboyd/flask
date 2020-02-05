# from solariat_bottle.db.predictors.customer_segment import CustomerSegment, CustomerMultiSegment
# from solariat_bottle.db.account import Account
# from solariat_bottle.db.agent_matching.profiles.customer_profile import CustomerProfile
#
# def test_single_segments():
#     account_id = Account.objects.find_one().id
#     CustomerProfile.objects.remove(id__ne=1)
#     CustomerSegment.objects.remove(id__ne=1)
#     CustomerMultiSegment.objects.remove(id__ne=1)
#     vip = CustomerSegment.objects.create(account_id=account_id,
#                                          display_name="VIP",
#                                          precondition="((account_balance > 10000) & (age < 30)) | (account_balance > 100000)",
#                                          acceptance_rule="account_balance > 1000000")
#
#     c_p1 = CustomerProfile.objects.get_or_create(age=75,
#                                                  account_id=account_id,
#                                                  account_balance=120000,
#                                                  sex='MALE')
#     c_p2 = CustomerProfile.objects.get_or_create(age=25,
#                                                  account_id=account_id,
#                                                  account_balance=12000,
#                                                  sex='FEMALE')
#     c_p3 = CustomerProfile.objects.get_or_create(age=50,
#                                                  account_id=account_id,
#                                                  account_balance=15000,
#                                                  sex='FEMALE')
#     c_p4 = CustomerProfile.objects.get_or_create(age=99,
#                                                  account_id=account_id,
#                                                  account_balance=1250000,
#                                                  sex='MALE')
#     print vip.match(c_p1), vip.score(c_p1)
#     print vip.match(c_p2), vip.score(c_p2)
#     print vip.match(c_p3), vip.score(c_p3)
#     print vip.match(c_p4), vip.score(c_p4)
#
#     print "------------------ FEEDBACK --------------------"
#     vip.accept(c_p3)
#     vip.reject(c_p4)
#     print vip.match(c_p1), vip.score(c_p1)
#     print vip.match(c_p2), vip.score(c_p2)
#     print vip.match(c_p3), vip.score(c_p3)
#     print vip.match(c_p4), vip.score(c_p4)
#
#
# def test_multiple_segments():
#     account_id = Account.objects.find_one().id
#     CustomerProfile.objects.remove(id__ne=1)
#     CustomerSegment.objects.remove(id__ne=1)
#     CustomerMultiSegment.objects.remove(id__ne=1)
#     new = CustomerSegment.objects.create(account_id=account_id,
#                                      display_name="NEW")
#     reg = CustomerSegment.objects.create(account_id=account_id,
#                                      display_name="REGULAR")
#     vip = CustomerSegment.objects.create(account_id=account_id,
#                                      display_name="VIP",
#                                      precondition="((account_balance > 10000) & (age < 30)) | (account_balance > 100000)",
#                                      acceptance_rule="account_balance > 1000000")
#     multi_class = CustomerMultiSegment.objects.create(account_id=account_id,
#                                                       abc_predictors=[new.id, reg.id, vip.id])
#
#     c_p1 = CustomerProfile.objects.get_or_create(age=75,
#                                                  account_id=account_id,
#                                                  account_balance=120000,
#                                                  sex='MALE')
#     c_p2 = CustomerProfile.objects.get_or_create(age=25,
#                                                  account_id=account_id,
#                                                  account_balance=12000,
#                                                  sex='FEMALE')
#     c_p3 = CustomerProfile.objects.get_or_create(age=50,
#                                                  account_id=account_id,
#                                                  account_balance=15000,
#                                                  sex='FEMALE')
#     c_p4 = CustomerProfile.objects.get_or_create(age=99,
#                                                  account_id=account_id,
#                                                  account_balance=1250000,
#                                                  sex='MALE')
#     print multi_class.match(c_p1), multi_class.score(c_p1)
#     print multi_class.match(c_p2), multi_class.score(c_p2)
#     print multi_class.match(c_p3), multi_class.score(c_p3)
#     print multi_class.match(c_p4), multi_class.score(c_p4)
#
#     multi_class.accept(c_p1, reg)
#     print multi_class.match(c_p1), multi_class.score(c_p1)
#     print multi_class.match(c_p2), multi_class.score(c_p2)
#     print multi_class.match(c_p3), multi_class.score(c_p3)
#     print multi_class.match(c_p4), multi_class.score(c_p4)
#
#
# def test_mongo_multikey_index():
#     from datetime import datetime
#     # start = datetime.now()
#     # CustomerProfile.objects.remove(id__ne=1)
#     # CustomerProfile.objects.coll.drop_indexes()
#     # print "Dropped old data in " + str(datetime.now() - start)
#     # start = datetime.now()
#     account_id = Account.objects.find_one().inbound
#     for idx in xrange(1000000):
#         chosen_tags = ['tag4', 'tag5'] if idx % 2 == 0 else ['tag5', 'tag6']
#         CustomerProfile.objects.create(account_id=account_id,
#                                        assigned_segments=chosen_tags)
#     for idx in xrange(1000000):
#         chosen_tags = ['tag7', 'tag8'] if idx % 2 == 0 else ['tag8', 'tag9']
#         CustomerProfile.objects.create(account_id=account_id,
#                                        assigned_segments=chosen_tags)
#     start = datetime.now()
#     CustomerProfile.objects.coll.drop_indexes()
#     for x in xrange(25):
#         CustomerProfile.objects.coll.find({'$and': [{'assigned_segments': 'tag2'}, {'assigned_segments': 'tag3'}]}
#                                           ).count()
#     # print CustomerProfile.objects.coll.find({'assigned_segments': 'tag2'}).count()
#     print "25 non indexed $and find query took " + str(datetime.now() - start)
#
#     start = datetime.now()
#     CustomerProfile.objects.coll.drop_indexes()
#     for x in xrange(25):
#         CustomerProfile.objects.coll.find({'assigned_segments': 'tag2'}).count()
#     # print CustomerProfile.objects.coll.find({'assigned_segments': 'tag2'}).count()
#     print "25 non indexed simple find query took " + str(datetime.now() - start)
#
#     CustomerProfile.objects.coll.ensure_index('assigned_segments')
#     start = datetime.now()
#     for x in xrange(25):
#         CustomerProfile.objects.coll.find({'$and': [{'assigned_segments': 'tag2'}, {'assigned_segments': 'tag3'}]}
#                                           ).count()
#     # print CustomerProfile.objects.coll.find({'assigned_segments': 'tag2'}).count()
#     print "25 $and indexed find query took " + str(datetime.now() - start)
#
#     start = datetime.now()
#     CustomerProfile.objects.coll.drop_indexes()
#     for x in xrange(25):
#         CustomerProfile.objects.coll.find({'assigned_segments': 'tag2'}).count()
#     # print CustomerProfile.objects.coll.find({'assigned_segments': 'tag2'}).count()
#     print "25 simple indexed simple find query took " + str(datetime.now() - start)
#
# test_single_segments()
# test_multiple_segments()
# #test_mongo_multikey_index()
#
# from solariat_bottle.db.agent_matching.profiles import CustomerProfile
#
# for c_p in CustomerProfile.objects():
#     c_p.refresh_segments()