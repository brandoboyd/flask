import solariat_bottle.api.exceptions as exc

import json
from pymongo.errors import InvalidOperation, BulkWriteError

from bson import ObjectId
from solariat_bottle.settings import LOGGER
from solariat_bottle.api.base import ModelAPIView, api_request
from solariat_bottle.db.auth import get_user_access_groups
from solariat_bottle.db.schema_based import apply_shema_type
from solariat.db.abstract import TYPE_STRING, TYPE_INTEGER, TYPE_BOOLEAN, TYPE_DICT, TYPE_LIST, KEY_NAME, KEY_TYPE
from solariat.db.abstract import FieldFactory


reversed_mapping = dict()
for key, val in FieldFactory.ACCEPTED_TYPES.iteritems():
    reversed_mapping[val] = key

def get_type_mapping(value):
    if type(value) in (int, float, long):
        return TYPE_INTEGER
    if type(value) in (str, unicode):
        return TYPE_STRING
    if type(value) in (bool, ):
        return TYPE_BOOLEAN
    if type(value) in (dict, ):
        return TYPE_DICT
    if type(value) in (list, tuple):
        return TYPE_LIST

BATCH_KEY = 'batch_data'
KEY_AGENT_LIST = 'agent_list'
KEY_NATIVE_ID = 'native_id'
KEY_RETURN_OBJECTS = 'return_objects'
DOT_REPLACEMENT_STR = '__DOT__'


class AgentsAPIView(ModelAPIView):
    endpoint = 'agents'
    # commands = ['score', 'feedback']

    @classmethod
    def register(cls, app):
        """ Queue API allows for extra commands, like 'fetch' and 'confirm' """
        url = cls.get_api_url()
        view_func = cls.as_view(cls.endpoint)
        app.add_url_rule(url, view_func=view_func, methods=['GET',])
        app.add_url_rule(url, view_func=view_func, methods=['POST',])
        app.add_url_rule(url, view_func=view_func, methods=['PUT',])
        app.add_url_rule(url, view_func=view_func, methods=['DELETE',])
        app.add_url_rule(cls.get_api_url('<_id>'),
                         view_func=view_func,
                         methods=['GET', 'PUT', 'DELETE'])
        # app.add_url_rule(cls.get_api_url('<command>/<on_call>'), view_func=view_func, methods=['POST'])
        app.add_url_rule(cls.get_api_url('<command>'), view_func=view_func, methods=['POST'])

        # url = cls.get_api_url('<command>')
        # app.add_url_rule(url, view_func=view_func, methods=["POST"])

    @classmethod
    def replace_dots_in_dict(cls, data, reverse=False):
        """
        Helper method to replace dots in API data dictionary (attached_data, skills) keys. Dots are replaced with string
        __DOT__. Mongo DB does not accept documents where keys contain dots in them.
        :param data: attached_data or skills dictionary received in API data
        :return: dictionary with keys containing dots modified
        """
        result = dict()

        for key, value in data.iteritems():
            if isinstance(value, dict):
                new_value = cls.replace_dots_in_dict(value, reverse)
            else:
                new_value = value

            if reverse:
                new_key = key.replace(DOT_REPLACEMENT_STR, '.')
            else:
                new_key = key.replace('.', DOT_REPLACEMENT_STR)

            result[new_key] = new_value

        return result
    # ------------------------------------ Start of handling CRUD requests ------------------------------------------
    @staticmethod
    def api_data_to_model_data(user, api_data, raw_db_fields=False,
                               fields_mapping=None, profile_schema=None, profile_class=None):
        """
        Helper to transform incoming API data to our model format.
        """
        if fields_mapping is None:
            fields_mapping = dict()
        agent_data = api_data
        for key, val in api_data.iteritems():
            if isinstance(val, dict):
                api_data[key] = AgentsAPIView.replace_dots_in_dict(val)

        if profile_schema is None:
            agent_profile_schema = user.account.agent_profile._get()
        else:
            agent_profile_schema = profile_schema

        if profile_class is None:
            AgentProfile = agent_profile_schema.get_data_class()
        else:
            AgentProfile = profile_class

        schema_changed = False
        for key in agent_data.keys():
            if key not in AgentProfile.fields:
                inferred_type = get_type_mapping(agent_data[key])
                if inferred_type:
                    if agent_profile_schema.schema:
                        agent_profile_schema.schema.append({KEY_NAME: key,
                                                            KEY_TYPE: inferred_type})
                        agent_profile_schema._data_cls = None
                    else:
                        agent_profile_schema.discovered_schema.append({KEY_NAME: key,
                                                                       KEY_TYPE: inferred_type})
                        agent_profile_schema._raw_data_cls = None
                    fields_mapping[key] = key
                    schema_changed = True
                else:
                    agent_data.pop(key)
            else:
                fields_mapping[key] = AgentProfile.fields[key].db_field
                field_type = reversed_mapping[AgentProfile.fields[key].__class__]
                try:
                    field_val = apply_shema_type(agent_data[key], field_type)
                    if isinstance(field_val, dict):
                        field_val = AgentsAPIView.replace_dots_in_dict(field_val)
                    agent_data[key] = field_val
                except Exception, ex:
                    LOGGER.error("Failed to apply schema for field %s and value %s. Got error %s" % (
                        key, agent_data[key], ex
                                                                                                    ))
                    agent_data.pop(key)

        if schema_changed:
            agent_profile_schema.save()
            AgentProfile = agent_profile_schema.get_data_class()
        #TODO: make this as default
        if raw_db_fields:
            agent_data_raw = {}
            for key, value in agent_data.iteritems():
                agent_data_raw[fields_mapping[key]] = value
            agent_data_raw['_t'] = [u'AgentProfile', u'BaseProfile', u'AuthDocument']
            agent_data_raw['account_id'] = user.account.id
            agent_data_raw['acl'] = get_user_access_groups(user)
            return agent_data_raw, AgentProfile, agent_profile_schema
        else:
            return agent_data, AgentProfile, agent_profile_schema

    # ------------------------------------ Start of handling PUT requests ------------------------------------------
    def __update_agent(self, user, agent_id, agent_data, AgentProfile, agent_profile_schema):
        if not agent_id:
            raise exc.InvalidParameterConfiguration("Expected required id for PUT requests: '{}'".format(agent_data))
        agent_data, AgentProfile, agent_profile_schema = self.api_data_to_model_data(user, agent_data,
                                                                                     profile_class=AgentProfile,
                                                                                     profile_schema=agent_profile_schema)
        agent = AgentProfile.objects.get(_id=ObjectId(agent_id))
        for field_name, field_value in agent_data.iteritems():
            setattr(agent, field_name, field_value)
        agent.save()
        return agent, AgentProfile, agent_profile_schema

    @api_request
    def _put(self, user, _id=None, *args, **kwargs):
        return_objects = kwargs.pop(KEY_RETURN_OBJECTS, False)
        agent_profile_schema = user.account.agent_profile._get()
        AgentProfile = agent_profile_schema.get_data_class()
        if BATCH_KEY in kwargs:
            batch = kwargs[BATCH_KEY]
            if type(batch) in (str, unicode):
                try:
                    batch = json.loads(batch)
                except Exception, ex:
                    return dict(ok=False, error="Invalid json: %s" % batch)

            bulk = AgentProfile.objects.coll.initialize_unordered_bulk_op()
            n_processed = 0
            for agent_data in batch:
                if KEY_NATIVE_ID not in agent_data and 'id' not in agent_data:
                    continue
                if 'id' in agent_data:
                    find_query = {"_id": ObjectId(agent_data['id'])}
                    agent_data['id'] = ObjectId(agent_data['id'])
                elif KEY_NATIVE_ID in AgentProfile.fields:
                    find_query = {AgentProfile.native_id.db_field: agent_data[KEY_NATIVE_ID]}
                else:
                    continue
                n_processed += 1

                parsed_data, AgentProfile, agent_profile_schema = self.api_data_to_model_data(user, agent_data,
                                                                                              raw_db_fields=True,
                                                                                              profile_class=AgentProfile,
                                                                                              profile_schema=agent_profile_schema)
                update_data = {'$set': parsed_data}
                bulk.find(find_query).upsert().update(update_data)
            try:
                result = bulk.execute()
            except InvalidOperation, ex:
                return dict(ok=False, error=str(ex))
            except BulkWriteError, ex:
                return dict(ok=False, error=str(ex.details))

            agent_profile_schema = user.account.agent_profile._get()
            agent_profile_schema.compute_cardinalities()
            if isinstance(result, dict):
                return dict(ok=True, nr_inserts=result['nUpserted'],
                            nr_updates=result['nModified'], nr_processed=n_processed)
            else:
                return dict(ok=False, error=str(result))
        else:
            agent_id = _id or kwargs.pop('id', None)
            result = self.__update_agent(user, agent_id, kwargs, AgentProfile, agent_profile_schema)[0]
            if return_objects:
                return self._format_single_doc(result)
            else:
                return dict(ok=True, nr_upserted=1)

    def put(self, command=None, batch_data=None, *args, **kwargs):
        return self._put(*args, **kwargs)
    # ------------------------------------ End of handling PUT requests ------------------------------------------

    # ------------------------------------ Start of handling DELETE requests ------------------------------------------
    @api_request
    def _delete(self, user, _id=None, *args, **kwargs):
        agent_profile_schema = user.account.agent_profile._get()
        AgentProfile = agent_profile_schema.get_data_class()
        agent_id = _id or kwargs.get('id', None)
        native_id = kwargs.get('native_id', None)
        if not agent_id and not native_id:
            raise exc.InvalidParameterConfiguration("Unsafe delete. Need to pass in id or native_id for deletion: '{}'".format(kwargs))
        if agent_id:
            AgentProfile.objects.remove_by_user(user, _id=ObjectId(agent_id))
        if native_id:
            AgentProfile.objects.remove_by_user(user, native_id=native_id)
        # Always 1 for now, this will be changed when batch comes into play
        return dict(removed_count=1)

    def delete(self, *args, **kwargs):
        return self._delete(*args, **kwargs)
    # ------------------------------------ End of handling DELETE requests ------------------------------------------

    # ------------------------------------ Start of handling POST requests ------------------------------------------
    def __create_agent(self, user, agent_data, AgentProfile, agent_profile_schema):
        if 'id' in agent_data:
            try:
                return self.__update_agent(user, agent_data['id'], agent_data)
            except AgentProfile.DoesNotExist, ex:
                raise exc.InvalidParameterConfiguration('No agent with id=%s found in db. Skipped record %s' %
                                                        (agent_data['id'], agent_data))
        else:
            agent_data, AgentProfile, agent_profile_schema = self.api_data_to_model_data(user, agent_data,
                                                                                         raw_db_fields=True,
                                                                                         profile_schema=agent_profile_schema,
                                                                                         profile_class=AgentProfile)

        agent_data['account_id'] = user.account.id
        LOGGER.debug("DEBUG_FAILURES: Creating agent in account %s and collection %s" % (user.account.id,
                                                                                         AgentProfile.objects.coll))
        return agent_data, AgentProfile, agent_profile_schema

    @api_request
    def post(self, user, command=None, _id=None, *args, **kwargs):
        """ The standard POST request. Create a new instance and returns the value in the same
         form as a GET request would. """
        agent_profile_schema = user.account.agent_profile._get()
        AgentProfile = agent_profile_schema.get_data_class()

        return_objects = kwargs.pop(KEY_RETURN_OBJECTS, False)
        if command and command == "loginstatus":
            return self._login_status(user, *args, **kwargs)
        else:
            if BATCH_KEY in kwargs:
                agents = []
                errors = []
                for agent_data in kwargs[BATCH_KEY]:
                    try:
                        parsed_agent, AgentProfile, agent_profile_schema = self.__create_agent(user,
                                                                                               agent_data,
                                                                                               AgentProfile,
                                                                                               agent_profile_schema)
                        agents.append(parsed_agent)
                    except Exception, ex:
                        errors.append(ex)
                bulk = AgentProfile.objects.coll.initialize_unordered_bulk_op()
                for agent in agents:
                    bulk.insert(agent)
                bulk.execute()
                agent_profile_schema.compute_cardinalities()

                if return_objects:
                    result_json = self._format_multiple_docs(agents)
                else:
                    result_json = dict(ok=True,
                                       nr_inserted=len(agents))

                if errors:
                    LOGGER.error(errors)
                    result_json['errors'] = [str(err) for err in errors]
                return result_json
            else:
                agent_data, AgentProfile, agent_profile_schema = self.__create_agent(user,
                                                                                     kwargs,
                                                                                     AgentProfile,
                                                                                     agent_profile_schema)
                agent = AgentProfile.objects.create_by_user(user, **agent_data)
                agent_profile_schema.compute_cardinalities()
                if return_objects:
                    result_json = self._format_single_doc(agent)
                else:
                    result_json = dict(ok=True,
                                       nr_inserted=1)
                return result_json

    def _login_status(self, user, *args, **kwargs):
        batch_data = kwargs['batch_data']
        agent_profile_schema = user.account.agent_profile._get()
        AgentProfile = agent_profile_schema.get_data_class()
        batch_data = json.loads(batch_data)
        if KEY_AGENT_LIST not in batch_data:
            raise exc.InvalidParameterConfiguration("Missing required parameter %s" % KEY_AGENT_LIST)
        if 'login_status' not in batch_data:
            raise exc.InvalidParameterConfiguration("Missing required parameter %s" % KEY_AGENT_LIST)

        login_status = batch_data['login_status']
        counter = 0
        for nid in batch_data[KEY_AGENT_LIST]:
            nid = str(nid)
            ap = AgentProfile.objects.get(native_id=nid)
            ap.attached_data['loginStatus'] = login_status
            ap.save()
            counter += 1
            LOGGER.info("UPDATE LOGIN STATUS COUNT: %s" % counter)
        return dict(ok=True, n_updates=counter)


    # ------------------------------------ End of handling POST requests ------------------------------------------

    # ------------------------------------ Start of handling GET requests -----------------------------------------
    @api_request
    def get(self, user, **kwargs):
        agent_profile_schema = user.account.agent_profile._get()
        AgentProfile = agent_profile_schema.get_data_class()

        LOGGER.info("DEBUG_FAILURES: Fetching agent in account %s and collection %s" % (user.account.id,
                                                                                        AgentProfile.objects.coll))
        debug = kwargs.get('debug_query', False)
        if 'id' in kwargs or '_id' in kwargs:
            agent_id = kwargs.get('id', kwargs.get('_id'))
            try:
                return dict(ok=True, item=self._format_doc(AgentProfile.objects.get(agent_id)))
            except AgentProfile.DoesNotExist:
                return dict(ok=False, error="No agent found with id " + str(agent_id))

        if 'native_id' in kwargs:
            agent_native_id = kwargs.get('native_id')
            try:
                return dict(ok=True, item=self._format_doc(AgentProfile.objects.get(native_id=agent_native_id)))
            except AgentProfile.DoesNotExist:
                LOGGER.error("No agent found with native_id=%s. Current native_ids were=%s and a total of %s agents" % (agent_native_id,
                             [ag.native_id for ag in AgentProfile.objects()], AgentProfile.objects.count()))
                return dict(ok=False, error="No agent found with native_id " + str(agent_native_id))

        account_id = kwargs.get('account_id') or user.account.id

        if 'filter' in kwargs and kwargs['filter']:
            query, debug_query = agent_profile_schema.construct_filter_query(kwargs['filter'],
                                                                             context=AgentProfile.fields.keys())
            query[AgentProfile.account_id.db_field] = account_id
            agents = AgentProfile.objects.find(**query)
        else:
            agents = AgentProfile.objects.find(account_id=account_id)
            debug_query = []

        response = dict(ok=True, list=[self._format_doc(ag) for ag in agents])
        if debug:
            response['query'] = debug_query
        return response

    @classmethod
    def _format_doc(cls, item):
        """ Format a post ready to be JSONified """
        if not isinstance(item, dict):
            result_dict = item.to_dict()
        else:
            result_dict = item
        result_dict.pop('groups', None)
        result_dict.pop('actor_num', None)
        for key, val in result_dict.iteritems():
            if isinstance(val, dict):
                result_dict[key] = AgentsAPIView.replace_dots_in_dict(val, reverse=True)
        return result_dict
    # ------------------------------------ End of handling GET requests ------------------------------------------


