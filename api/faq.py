from solariat_bottle.api.base import ModelAPIView, api_request
import solariat_bottle.api.exceptions as exc
# from solariat_bottle.db.next_best_action.controller import NextBestActionEngine
from solariat_bottle.db.channel.base import Channel
from solariat_bottle.db.faq import FAQ, DbBasedSE1
from solariat_bottle.db.post.faq_query import FAQQueryEvent
from solariat_bottle.settings import LOGGER


class FAQAPIView(ModelAPIView):

    commands = ['train', 'search']
    model = FAQ
    endpoint = 'faq'
    required_fields = ['channel', 'question', 'answer']

    @classmethod
    def register(cls, app):
        """ Queue API allows for extra commands, like 'fetch' and 'confirm' """
        url = cls.get_api_url()
        view_func = cls.as_view(cls.endpoint)
        app.add_url_rule(url, view_func=view_func, methods=['GET', "POST", "PUT", "DELETE"])
        url = cls.get_api_url('<command>')
        app.add_url_rule(url, view_func=view_func, methods=["GET", "POST", "PUT", "DELETE"])

    def get(self, *args, **kwargs):
        return self._get(*args, **kwargs)

    @api_request
    def put(self, user, *args, **kwargs):
        if 'id' not in kwargs:
            raise exc.InvalidParameterConfiguration("Need the id of the FAQ you want to update.")
        try:
            faq = FAQ.objects.get(kwargs['id'])
        except FAQ.DoesNotExist:
            raise exc.ResourceDoesNotExist("No FAQ with id=%s" % kwargs['id'])
        if 'question' in kwargs:
            faq.question = kwargs['question']
        if 'answer' in kwargs:
            faq.answer = kwargs['answer']
        faq.save()
        DbBasedSE1(faq.channel).compile_faqs()
        return dict(item=faq.to_dict())

    def delete(self, *args, **kwargs):
        return self._delete(*args, **kwargs)

    def post(self, command=None, *args, **kwargs):
        """ Allowed commands are routed to the _<command> method on this class """
        if command in self.commands:
            meth = getattr(self, '_' + command)
            return meth(*args, **kwargs)
        return self._post(*args, **kwargs)

    def __sample_train(self, faq_id, query, value):
        faq = FAQ.objects.get(faq_id)
        faq.train(query, value)

    @api_request
    def _train(self, user, *args, **kwargs):
        error_desc = "Requests should either contain a list of samples in the form: "
        error_desc += "{'samples': [(<'faq_id', 'query', 'value'>), ...]}"
        error_desc += " or a simple entry {'faq_id': <>, 'query': <>, 'value': <>}"
        if 'samples' in kwargs:
            # A batch of data passed in
            errors = []
            result = []
            for sample in kwargs['samples']:
                try:
                    result.append(self.__sample_train(*sample))
                except FAQ.DoesNotExist:
                    errors.append("No faq exists with id=%s. Skipping related sample." % sample[0])
            result = dict(ok=len(errors) == 0,
                          list=result)
            result['skipped_samples'] = len(errors)
            result['errors'] = list(set(errors))
            return result
        else:
            required_params = ['faq_id', 'query', 'value']
            for entry in required_params:
                if entry not in kwargs:
                    error_msg = "Missing required parameter '%s'" % entry
                    raise exc.InvalidParameterConfiguration(error_msg, description=error_desc)
            return dict(item=self.__sample_train(kwargs['faq_id'], kwargs['query'], kwargs['value']))

    @api_request
    def _search(self, user, *args, **kwargs):
        error_desc = "Requests should contain a channel id and some query text: {'channel': <>, 'query': <>}"
        required_params = ['channel', 'query']
        LOGGER.debug('Searching for FAQs with params: %s' % kwargs)
        for entry in required_params:
            if entry not in kwargs:
                error_msg = "Missing required parameter '%s'" % entry
                raise exc.InvalidParameterConfiguration(error_msg, description=error_desc)
        try:
            channel = Channel.objects.get(kwargs['channel'])
        except Channel.DoesNotExist:
            raise exc.ResourceDoesNotExist("No channel with id=%s found in the system." % kwargs['channel'])
        result = FAQ.objects.text_search(channel, kwargs['query'], limit=100)
        LOGGER.debug('Search results for FAQs: %s' % result)
        from solariat.utils.timeslot import parse_datetime, now
        _created = parse_datetime(kwargs.get('_created', now()), default=now())
        faq_event = FAQQueryEvent.objects.create_by_user(user, query=kwargs['query'], channels=[channel.id], _created=_created)
        if 'customer_id' in kwargs:
            CustomerProfile = user.account.get_customer_profile_class()
            customer = CustomerProfile.objects.get(kwargs['customer_id'])
            # import ipdb
            # ipdb.set_trace()
            # actions = NextBestActionEngine.upsert(account_id=customer.account_id).search(faq_event, customer)
            # TODO: THink how we can implement this properly with new advisors API
            return dict(list=result, event=faq_event.to_dict()) #, actions=actions)
        else:
            return dict(list=result, event=faq_event.to_dict())


