import json
from datetime import timedelta
from itertools import chain
from operator import attrgetter
from solariat_bottle.configurable_apps import APP_JOURNEYS
from werkzeug.utils import cached_property
from bson.objectid import ObjectId

from solariat.db import fields
from solariat.db.abstract import SonDocument
from solariat.utils.timeslot import utc, TIMESLOT_EPOCH, now, parse_datetime

from solariat_bottle.db.sequences import NumberSequences
from solariat_bottle.db.user import User, get_user
from solariat_bottle.db.user_profiles.user_profile import UserProfile
from solariat_bottle.db.channel.base import (
        ChannelsAuthDocument, Channel, ChannelsAuthManager, SmartTagChannel)
from solariat_bottle.db.predictors.abc_predictor import ABCPredictor
from solariat_bottle.settings import LOGGER, get_var
from solariat_bottle.utils.id_encoder import pack_event_id, unpack_event_id
from solariat_bottle.db.auth import Document
from solariat_bottle.db.dynamic_profiles import DynamicImportedProfile
from solariat_bottle.db.events.event_type import BaseEventType


class EventManager(ChannelsAuthManager):

    def create_by_user(self, user, **kw):
        kw.pop('safe_create', None)
        event = super(EventManager, self).create_by_user(user=user, **kw)
        return event

    def create(self, _id=None, **kw):
        '''
        For directly creating an event with params provided.
        '''
        self._handle_create_parameters(_id, kw)
        event = super(EventManager, self).create(**kw)
        self.postprocess_event(event)
        return event

    def postprocess_event(self, event):
        if isinstance(event, ObjectId):
            event = self.get(event)
        for account, channels in event.channels_by_account.viewitems():
            if account and APP_JOURNEYS in account.available_apps:
                event.assign_smart_tags()
                # event.compute_journey_information(account)

    def get(self, *args, **kwargs):
        if len(args) == 1 and isinstance(args[0], (str, unicode)) and args[0].isdigit():
            id_ = long(args[0]) if str(args[0]).isdigit() else args[0]
            return super(EventManager, self).get(id_, **kwargs)
        if not args and kwargs.get('id', False):
            kwargs['id'] = long(kwargs['id']) if str(kwargs['id']).isdigit() else kwargs['id']
        return super(EventManager, self).get(*args, **kwargs)

    def events_for_actor(self, start, end, actor_num):
        id_lower_bound = pack_event_id(actor_num, utc(start))
        id_upper_bound = pack_event_id(actor_num, utc(end))
        if id_lower_bound == id_upper_bound:
            res = self.find(id=id_upper_bound)
        else:
            res = self.find(id__lte=id_upper_bound, id__gte=id_lower_bound)
        return res

    def range_query(self, start, end, customer, skip=0, limit=None):
        assert isinstance(customer, DynamicImportedProfile)
        actor_nums = [profile.actor_num for profile in customer.linked_profiles]
        actor_nums.append(customer.actor_num)

        from solariat.utils.iterfu import merge
        queries = [self.events_for_actor(start, end, actor_num) for actor_num in set(actor_nums)]
        # merge(*queries, key=attrgetter('created_at'))    Removing key to sort by for PRR-174 -- Sabr
        for event in merge(*queries):
            for i in range(skip):
                continue
            if limit is not None:
                limit -= 1
            if limit == 0:
                raise StopIteration
            yield event

    def range_query_count(self, start, end, customer, skip=0, limit=0):
        '''
        Fetch all events for a customer. This will look at the linked profiles for the
        customer so that we can obtain a complete event sequence across channels in one
        shot.
        '''
        actor_nums = [profile.actor_num for profile in customer.linked_profiles]
        actor_nums.append(customer.actor_num)
        queries = [self.events_for_actor(start, end, actor_num) for actor_num in set(actor_nums)]
        return sum(query.skip(skip).limit(limit).count() for query in queries)

    def lookup_history(self, event, lookback_window):
        actor_num, _ = unpack_event_id(event.id)

        id_lower_bound = pack_event_id(actor_num, utc(event._created - timedelta(seconds=lookback_window)))
        id_upper_bound = pack_event_id(actor_num, utc(event._created))
        event_sequence = self.find(id__lte=id_upper_bound, id__gte=id_lower_bound)[:]
        return event_sequence

    def customer_history(self, customer, limit=10):
        raise RuntimeError("call Event.customer_history")
        assert isinstance(customer, DynamicImportedProfile)
        id_upper_bound = pack_event_id(customer.actor_num, now())
        id_lower_bound = pack_event_id(customer.actor_num, now() - timedelta(seconds=120))
        return self.find(id__lte=id_upper_bound, id__gte=id_lower_bound).limit(limit).sort(id=-1)[:limit]

    def _handle_create_parameters(self, _id, kw):
        '''
        This function handles pre-processing of parameters so that events are loaded
        with correct parameter mapping for native ids and links to pervious events.

        Sets:
        *  _user_profile from user_profile or actor_id
        * _created - will be used ot set with current time
        * in_reply_to_native_id
        * parent_event
        * id creation

        kw already must contain:
        * actor_id  - usually created in tasks.normalize_post_params
        * is_inbound - to determine and bind event exact to customer
        * event_type - display_name or instance of BaseEventType
        '''
        if 'user_profile' in kw:
            if not get_var('ON_TEST', False):  # _obtain_user_profile creates anonymous UserProfile
                assert isinstance(kw['user_profile'], self.doc_class.PROFILE_CLASS), \
                    "(%s) %s is not instance of %s\ndata:\n%s" % \
                    (type(kw['user_profile']),
                     kw['user_profile'],
                     self.doc_class.PROFILE_CLASS,
                     str(kw['user_profile'].data))

            assert _id, 'Id must be generated earlier, with corresponding dynamic ustomer profile'
            kw['_user_profile'] = kw.pop('user_profile').id

        if 'channels' in kw:
            kw['channels'] = [(c.id if isinstance(c, Channel) else c) for c in kw['channels']]

        # actor_id must be set on kw earlier, we bind event to actor_id
        actor_id = kw['actor_id']
        if not kw.get('_created'):
            kw['_created'] = now()

        in_reply_to_native_id = kw.pop('in_reply_to_native_id', None)
        parent_event = kw.pop('parent_event', None)
        event_type = kw.get('event_type')
        if isinstance(event_type, BaseEventType):
            kw['event_type'] = event_type.display_name

        # TODO: pass actor_num instead actor_id
        kw['id'] = long(
            _id or self.doc_class.gen_id(
                kw['is_inbound'],
                actor_id, kw['_created'],
                in_reply_to_native_id,
                parent_event
            )
        )

        # Make sure we strip out reference to 'native_id' key. Use it if it is there. If not
        # then try for _native_id, or as a last resort, set the native_id to be based directly
        # in the id.
        kw['_native_id'] = kw.pop('native_id', kw.get('_native_id', str(kw['id'])))

    def _prepare_post_checking_duplicates(self, klass, **kw):
        """Generates post_id, checks for duplicates and creates post"""

        actual_channels = [(c.id if isinstance(c, Channel) else c) for c in list(kw['channels'])]
        lang_data = kw.pop('lang', None)
        native_id = kw.pop('native_id',  None)

        from pymongo.errors import DuplicateKeyError

        # Some events lack ms resolution on time stamps. So we
        # need to pad the timestampe with additional resolution. We compute
        # this as a hash of the native_id.
        from solariat_bottle.utils.hash import mhash
        from solariat_bottle.utils.id_encoder import MILLISECONDS_PER_SECOND
        padding = mhash(native_id, n=20) % MILLISECONDS_PER_SECOND

        p_id = kw.pop('_id', self.gen_id(padding=padding, **kw))

        # Now reset the native id if we were not provided one.
        native_id = native_id if native_id else str(p_id)

        if lang_data:
            kw['_lang_code'] = lang_data.lang

        try:
            post = klass.create(self, _id=p_id, _native_id=native_id, **kw)
            return post, False
        except DuplicateKeyError:
            # If it is a duplicate, fetch the original and update the channels. Note that this use case can
            # probably ne handled with an UPSERT and just set the new channels to this actual_channels
            # list. Not clear which some channels would not be passed in but are still necessary.
            post = self.find_one(_id=p_id)
            post.channels = list(set(post.channels) | set(actual_channels))
            return post, False

        return None, True

class JourneyTypeStagePair(SonDocument):
    journey_type_id = fields.ObjectIdField('t')
    journey_stage_id = fields.ObjectIdField('s')

    @property
    def journey_type(self):
        from solariat_bottle.db.journeys.journey_type import JourneyType

        return JourneyType.objects.get(id=self.journey_type_id)

    @property
    def journey_stage(self):
        from solariat_bottle.db.journeys.journey_type import JourneyStageType

        return JourneyStageType.objects.get(self.journey_stage_id)

    @property
    def id(self):
        return str(self.journey_type_id), str(self.journey_stage_id)


class Score(SonDocument):
    name = fields.StringField()
    score = fields.NumField()

    def __hash__(self):
        return hash(self.id)

    @property
    def id(self):
        return self.name, str(self.score)


class Event(ChannelsAuthDocument):

    manager = EventManager
    collection = "Post"
    allow_inheritance = True

    id = fields.EventIdField(db_field='_id', unique=True, required=True)

    _created = fields.DateTimeField(db_field='_created',
                                    default=now, required=True)

    # TODO: [gsejop] actor_id and is_inbound might not be needed
    actor_id = fields.BaseField(db_field='ad')
    is_inbound = fields.BooleanField(db_field='ii')

    stage_metadata = fields.StringField(db_field='smd')

    assigned_tags = fields.ListField(fields.StringField())
    rejected_tags = fields.ListField(fields.StringField())
    # Single event tags
    # computed_single_tags = fields.ListField(fields.StringField())
    # single_tag_scores = fields.ListField(fields.DictField())
    #
    # # Multi event tags
    # computed_multi_tags = fields.ListField(fields.StringField())
    # multi_tag_scores = fields.ListField(fields.DictField())

    _computed_tags = fields.ListField(fields.StringField(), db_field='cts')
    computed_scores = fields.ListField(fields.EmbeddedDocumentField(Score), db_field='css')

    reward_data = fields.DictField(db_field='rd')   # Any reward information we have about a specific event
    _journey_stages = fields.ListField(fields.ObjectIdField(), db_field='js')
    # More client friendly way of passing in journey information. JourneyName__StageName
    journey_mapping = fields.ListField(fields.StringField(), db_field='jm')

    # Optional and channel specific (e.g. Twitter: tweet/retweet/PM, Web: click/search)
    event_type = fields.StringField()

    # for dynamic events importing
    import_id = fields.NumField()
    _was_processed = fields.BooleanField(db_field='_wp', default=False)

    _native_id = fields.StringField(db_field='_n', required=True, unique=True)

    PROFILE_CLASS = UserProfile

    indexes = ['_was_processed']


    @property
    def native_id(self):
        return self._native_id

    def __init__(self, *args, **kw):
        if '_created' not in kw:
            kw['_created'] = now()

        if '_native_id' not in kw:
            kw['_native_id'] = str(now())

        super(Event, self).__init__(*args, **kw)

    def set_dynamic_class(self, inheritance):
        ''' Support dynamic events '''

        if DynamicEvent.__name__ in inheritance:
            # from solariat_bottle.db.dynamic_event import EventType
            from solariat_bottle.db.events.event_type import BaseEventType

            event_type_name = self.data[DynamicEvent.event_type.db_field]
            # event_type = EventType.objects.find_one(event_type_id)
            # TODO: check using get_user() is correct here
            acc_id = get_user().account.id
            LOGGER.debug('Set event dynamic class, use acc: %s for find event types', acc_id)
            event_type = BaseEventType.objects.find_one_by_display_name(acc_id, event_type_name)

            if event_type:
                dyn_cls = event_type.get_data_class()  # initialize class in Registry
                self.__class__ = dyn_cls
            else:
                LOGGER.error('Cannot find suitable event type for dynamic class!')

    def _is_inbound(self, account=None):
        if account is None:
            return None

        from solariat_bottle.db.account import Account
        assert isinstance(account, Account)
        account_channels = Channel.objects(id__in=self.channels, account=account)
        is_inbound = {channel.is_inbound for channel in account_channels}
        if len(is_inbound) == 0:
            return None
        if len(is_inbound) != 1:
            LOGGER.warning("Channel misconfiguration for account %s. "
                           "Event splitted between inbound and outbound channels." % account)
            return None
        return all(is_inbound)

    def customer_profile(self, account):
        CustomerProfile = account.get_customer_profile_class()
        customer_profile = CustomerProfile.objects.find_one(id=self.actor_id)
        if customer_profile:
            return customer_profile

        customer_profile = None
        if self.is_inbound or self._is_inbound(account):
            actor_num, _ = unpack_event_id(self.id)
            customer_profile = CustomerProfile.objects.find_one(actor_num=actor_num)
        elif hasattr(self, 'parent'):
            try:
                parent = self.parent
                if parent and parent.is_inbound:
                    actor_id = parent.actor_id
                    customer_profile = CustomerProfile.objects.find_one(id=actor_id)
                else:
                    actor_num, _ = unpack_event_id(self.id)
                    customer_profile = CustomerProfile.objects.find_one(actor_num=actor_num)
            except (AttributeError, Event.DoesNotExist):
                LOGGER.info("Could not get actor_id from parent post of {} {}".format(self, account))

        return customer_profile

    def get_event_type(self, account):
        from solariat_bottle.db.events.event_type import BaseEventType
        return BaseEventType.objects.get_by_display_name(account.id, self.event_type)

    @property
    def journey_stages(self):
        from solariat_bottle.db.journeys.journey_type import JourneyStageType, JourneyType
        from solariat_bottle.db.journeys.customer_journey import CustomerJourney, JourneyStage

        if self._journey_stages:
            # Already computed them or were passed in
            return JourneyStageType.objects.find(id__in=self._journey_stages)

        channels_by_account = self.channels_by_account
        accounts = set(channels_by_account)
        result = []

        for account in accounts:
            # Need to compute any that apply

            journey_types_ids = [jt.id for jt in JourneyType.objects.find(account_id=account.id)]
            if self.event_type:
                event_type = self.get_event_type(account)

                # TODO: change JourneyStageType to use event_type name instead of ID?
                candidates = JourneyStageType.objects.find(account_id=account.id,
                                                           event_types=event_type.id,
                                                           journey_type_id__in=journey_types_ids)[:]
                if not candidates:
                    return result
                for candidate in candidates:
                    if candidate.evaluate_event(self):
                        result.append(candidate)

            if not result and self.event_type:
                # Nothing new, consider all current active journeys
                # The actual candidates then are the current stages on all journeys
                customer = self.customer_profile(account)
                if customer:
                    customer_journeys = CustomerJourney.objects.find(
                        account_id=account.id,
                        customer_id=customer.id,
                        status=JourneyStageType.IN_PROGRESS)[:]
                    for journey in customer_journeys:
                        current_stage = JourneyStage.objects.get(journey.current_stage)
                        current_stage_type = JourneyStageType.objects.get(current_stage.stage_type_id)
                        result.append(current_stage_type)
        self._journey_stages = [stage.id for stage in result]
        return result

    @property
    def datetime_from_id(self):
        return unpack_event_id(self.id)[1]

    @property
    def computed_tags(self):
        if hasattr(self, 'accepted_smart_tags'):
            res = [str(smt.id) for smt in self.accepted_smart_tags]
        else:
            res = []
        res = list(set(self._computed_tags + res + self.assigned_tags))
        return res

    @property
    def json_computed_tags(self):
        computed_tags = []
        for tag_id in self.computed_tags:
            try:
                tag = SmartTagChannel.objects.get(tag_id)
                tag_title = tag.title
            except:
                tag = ABCPredictor.objects.get(tag_id)
                tag_title = tag.display_name
            computed_tags.append({'id': tag_id, 'title': tag_title})
        return computed_tags

    @property
    def journey_tags(self):
        j_tags = ABCPredictor.objects.find(id__in=self.computed_tags)[:]
        res = []
        if j_tags is not None:
            res = [dict(id=str(tag.id), title=tag.display_name) for tag in j_tags]
        return res

    @property
    def computed_single_tags(self):
        from solariat_bottle.db.predictors.multi_channel_smart_tag import SingleEventTag
        return SingleEventTag.objects.find(id__in=self.computed_tags)[:]

    @property
    def computed_multi_tags(self):
        from solariat_bottle.db.predictors.multi_channel_smart_tag import MultiEventTag
        return MultiEventTag.objects.find(id__in=self.computed_tags)[:]

    @property
    def computed_tag_objects(self):
        return self.computed_single_tags + self.computed_multi_tags

    @staticmethod
    def platform_created_at(platform_data):
        if not platform_data:
            return None
        return platform_data.get('created_at', None)

    @classmethod
    def patch_post_kw(cls, kw, native_data=None):
        if not kw.get('_created'):
            created_at = native_data and cls.platform_created_at(native_data) or None
            created_time = parse_datetime(created_at, default=now())
            # some facebook entities like images may have created_at=1999-01-01T08:00:00 +0000
            # which is before TIMESLOT_EPOCH and causes AssertError in pack_event_id
            if created_time <= TIMESLOT_EPOCH:
                wrapped_data = native_data.get('_wrapped_data', {})
                if not isinstance(wrapped_data, dict):
                    try:
                        wrapped_data = json.loads(wrapped_data)
                    except (ValueError, TypeError):
                        wrapped_data = {}
                updated_at = native_data.get('updated_time') or wrapped_data.get('updated_time', None)
                created_time = parse_datetime(updated_at, default=now())
                if created_time < TIMESLOT_EPOCH:
                    created_time = now()
            kw['_created'] = created_time
        channel = kw.get('channel') or kw['channels'][0]
        channel = channel if isinstance(channel, Channel) else Channel.objects.get(id=channel)
        # account = channel.account
        user_profile = kw.get('user_profile')
        # TODO: [gsejop] is_inbound should not be a posted property,
        #  event is routed to a set of channels
        # Apparently, is_inbound and actor_id are just extra helping information
        # sent from jop data generation script
        kw['is_inbound'] = kw.pop('is_inbound', channel.is_inbound)
        # if not kw.get('actor_id', False):
        #     if kw['is_inbound'] == True:
        #         kw['actor_id'] = user_profile.customer_profile.id
        #     elif kw['is_inbound'] == False:
        #         kw['actor_id'] = user_profile.agent_profile.id
        #     else:
        #         raise Exception('is_inbound should be set')
        kw.setdefault('actor_id', user_profile.id)
        return kw

    @classmethod
    def gen_id(cls, is_inbound, actor_id, _created, in_reply_to_native_id, parent_event=None):
        # Read The actor. This can result in multiple reads across different profile classes
        # which is very expensive. Need to cache this or find a more efficient concept that
        # does not require a read. TODO: pass actor_num directly
        actor_num = cls.get_actor(is_inbound, actor_id).actor_num

        # This is required so that we can efficiently query an event sequence with a range
        # query and a customer id. To do that we must figure out if there is a parent event
        # that is inbound. Only need to worry about this case if this event is outbound!
        if in_reply_to_native_id and not is_inbound:
            try:
                parent_event = Event.get_by_native_id(in_reply_to_native_id)
            except cls.DoesNotExist:
                pass
            else:
                actor_num = parent_event.actor.actor_num
        elif parent_event:
            assert isinstance(parent_event.actor, (UserProfile, DynamicImportedProfile)), parent_event.actor
            actor_num = parent_event.actor.actor_num

        # Finally, the id is an actor number and a time stamp, and will always be a Customer.
        return pack_event_id(actor_num, _created)

    @classmethod
    def get_by_native_id(cls, native_id):
        # Use native id field to fetch the required key
        return cls.objects.get(_native_id=native_id)

    @property
    def actor(self):
        return Event.get_actor(self.is_inbound, self.actor_id)

    @classmethod
    def get_actor(cls, is_inbound, actor_id, account=None):
        if account == None:
            from solariat_bottle.db.user import get_user
            account = get_user().account

        if is_inbound:
            DynProfileClass = account.get_customer_profile_class()
        else:
            DynProfileClass = account.get_agent_profile_class()

        # profile already must be created in tasks._obtain_user_profile
        try:
            profile = DynProfileClass.objects.get(actor_id)
        except DynProfileClass.DoesNotExist:
            # TODO: move out for dynamic events imports
            LOGGER.debug('TODO: this is only case for importing dyn events.'
                         'move creating profile outside (like in normalize_post_params)')
            profile = DynProfileClass(id=actor_id)
            profile.save()
        return profile

    # @cached_property
    # def customer_id(self):
    #     customer_id, _ = unpack_event_id(self.id)
    #     return customer_id

    def to_dict(self, fields2show=None):
        base_dict = super(Event, self).to_dict(fields2show=fields2show)
        base_dict['id'] = str(base_dict['id'])  # Make sure we work with strings instead of longs so we don't lose precision
        base_dict.pop('_journey_stages')
        return base_dict

    @property
    def created_at(self):
        return utc(self.created)

    @property
    def created(self):
        if utc(self._created) == TIMESLOT_EPOCH:
            self._created = self.parse_created_at() or now()
            self.save()
        return utc(self._created)

    def parse_created_at(self):
        return None

    @property
    def event_tags(self):
        from solariat_bottle.db.predictors.multi_channel_smart_tag import EventTag
        tag_ids = [t.id for t in (self.computed_single_tags + self.computed_multi_tags)] + self.assigned_tags
        for rejected_tag in self.rejected_tags:
            if rejected_tag in tag_ids:
                tag_ids.remove(rejected_tag)
        return EventTag.objects(id__in=tag_ids)[:]

    def assign_tags(self, tag_class):
        scores = []
        assigned_tags = []
        for intention_tag in tag_class.objects(channels__in=self.channels):
            if str(intention_tag.id) in self.assigned_tags:
                score = 1
            elif str(intention_tag.id) in self.rejected_tags:
                return 0
            else:
                score = intention_tag.score(self)
            scores.append(Score(name=intention_tag.display_name, score=score))
            if score > intention_tag.inclusion_threshold:
                assigned_tags.append(str(intention_tag.id))
        self._computed_tags = list(set(assigned_tags).union(set(self._computed_tags)))
        self.computed_scores = list(set(scores).union(set(self.computed_scores)))
        self.save()

    def assign_smart_tags(self):
        from solariat_bottle.db.predictors.multi_channel_smart_tag import SingleEventTag
        from solariat_bottle.db.predictors.multi_channel_smart_tag import MultiEventTag
        self.computed_scores = []
        self._computed_tags = []
        self.assign_tags(SingleEventTag)
        self.assign_tags(MultiEventTag)
        # self.assign_single_event_tags() # First, so we can use them as features for multi
        # self.assign_multi_event_tags()
        self.save()

    def get_customer_journeys(self, account):
        from solariat_bottle.db.journeys.customer_journey import CustomerJourney

        customer = self.customer_profile(account)
        if customer:
            return CustomerJourney.objects(customer_id=customer.id)[:]
        else:
            return []

    # def compute_journey_information(self, account):
    #     from solariat_bottle.db.journeys.customer_journey import CustomerJourney
    #
    #     customer = self.customer_profile(account)
    #     if customer:
    #         customer_id = customer.id
    #     else:
    #         return
    #     customer_journey = None
    #     journey_stages = self.journey_stages
    #     if journey_stages:
    #         # Journey information was specifically passed in, could be transition of stage
    #         # or just event relevant for a specific stage
    #         for stage in journey_stages:
    #             journey_type_id = stage.journey_type_id
    #             try:
    #                 from solariat_bottle.db.journeys.journey_type import JourneyType
    #                 customer_journey = CustomerJourney.objects.get(customer_id=customer_id,
    #                                                                journey_type_id=journey_type_id,
    #                                                                account_id=stage.account_id)
    #             except CustomerJourney.DoesNotExist:
    #                 customer_journey = CustomerJourney.objects.create(customer_id=customer_id,
    #                                                                   journey_type_id=journey_type_id,
    #                                                                   start_date=self.created_at,
    #                                                                   account_id=stage.account_id)
    #             customer_journey.process_event(self, stage, account)
    #     # else:
    #     for journey in CustomerJourney.objects(customer_id=customer_id):
    #         # Also process rest of the journeys
    #         # if journey != customer_journey:
    #         if (not customer_journey or journey.id != customer_journey.id
    #                 or journey.id == customer_journey.id and self.reward_data):
    #             journey.process_event(self, account=account)

    def add_tag(self, tag):
        self.assigned_tags.append(str(tag.id))
        if str(tag.id) in self.rejected_tags:
            self.rejected_tags.remove(str(tag.id))
        tag.accept(self)
        self.save()

    def remove_tag(self, tag):
        self.rejected_tags.append(str(tag.id))
        if str(tag.id) in self.assigned_tags:
            self.assigned_tags.remove(str(tag.id))
        tag.reject(self)
        self.save()

    def apply_smart_tags_to_journeys(self):
        for account in self.channels_by_account.viewkeys():
            if APP_JOURNEYS in account.available_apps:
                [j.apply_smart_tags(self) for j in self.get_customer_journeys(account)]

    @classmethod
    def import_data(cls, user, channel, data_loader):
        from solariat_bottle.db.post.utils import factory_by_user
        from solariat_bottle.db.events.event_type import StaticEventType

        static_event_types_map = {et.id: et for et in StaticEventType.objects.find()}

        stats = {'total': 0, 'success': 0}
        for idx, raw_data in enumerate(data_loader.load_data()):
            if isinstance(raw_data, tuple):  # JsonDataLoader returns (event_type, data) tuples
                event_type_id, raw_data = raw_data
                # check we can import this event to this channel
                event_type = static_event_types_map.get(event_type_id) # TODO: wrong!
                if event_type and event_type.platform != channel.platform.lower():
                    continue

            stats['total'] += 1
            raw_data.pop('channel', None)
            raw_data.pop('channels', None)
            raw_data['channel'] = channel
            try:
                factory_by_user(user, **raw_data)
            except:
                LOGGER.warning("Cannot import post #%d %s", idx, raw_data, exc_info=True)
            else:
                stats['success'] += 1
        return stats


class DynamicEventManager(EventManager):

    # for creating via factory_by_user / create_post
    def create_by_user(self, user, **kw):
        event_type = kw['event_type']
        kw['is_inbound'] = all([ch.is_inbound for ch in kw['channels']])

        native_field = event_type.native_id_field
        if native_field and native_field in kw:
            kw['_native_id'] = kw.pop(native_field)

        kw.pop('lang', None)
        kw.pop('content', None)
        kw.pop('speech_acts', None)
        kw.pop('_platform', None)
        kw.pop('sync', None)
        kw.pop('add_to_queue', None)

        return super(DynamicEventManager, self).create_by_user(user=user, **kw)


class DynamicEvent(Event):

    manager = DynamicEventManager

    event_type_id = fields.ObjectIdField()

    # def set_dynamic_class(self, inheritance):
    #     # we won't change class if it is created from event_type.create_data_class()
    #     pass
