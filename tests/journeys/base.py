from solariat_bottle.configurable_apps import APP_JOURNEYS, CONFIGURABLE_APPS
from solariat.tests.base import LoggerInterceptor
from solariat_bottle.tests.base import UICaseSimple

from solariat_bottle.db.roles import ADMIN


class JourneyByPathGenerationTest(UICaseSimple):
    _account_configured = False

    def _setup_user_account(self, email='super_user@solariat.com', account='QA'):
        if self._account_configured:
            return self.user, self.account, self.password

        import os
        password = os.urandom(32).encode('hex')
        su = self._create_db_user(email, password, roles=[ADMIN], is_superuser=True, account=account)

        user = su
        account = user.account
        account.available_apps = CONFIGURABLE_APPS
        account.selected_app = APP_JOURNEYS
        account.save()
        self.user = su
        self.account = account
        self.password = password
        self._account_configured = True
        return self.user, self.account, self.password

    def _setup_journey_params_generator(self, paths, stick_to_paths=False):

        import itertools
        from solariat_bottle.scripts.data_load.generate_gforce_demo import (
            get_journey_paths_index, map_slice, make_key, initialize_journey_types,
            initialize_journey_tags, setup_channels_and_tags, generate_event_types)
        
        user, account, password = self._setup_user_account()

        from solariat_bottle.scripts.data_load.demo_helpers.api_client import client
        client.options.base_url = ""
        client.options.password = password

        all_smts = setup_channels_and_tags(user, account)
        all_event_types = generate_event_types()
        journey_types = initialize_journey_types(user, account, all_event_types)
        journey_tags = initialize_journey_tags(user, account, journey_types, all_smts)

        journey_type_by_name = {jt.display_name: jt for jt in journey_types}
        journey_paths_index = get_journey_paths_index(paths)
        available_journey_types = list(set(journey_type for (journey_type, path) in map_slice(paths)))
        available_journey_types_num = len(available_journey_types)
        if stick_to_paths:
            journey_type_names = iter([x[0] for x in paths])
        else:
            journey_type_names = itertools.cycle(available_journey_types)

        def gen_params(customer_journey_counts):
            for customer_profile, journey_count in customer_journey_counts:
                journey_count = min(available_journey_types_num, journey_count)
                customer_journey_count = 0
                while customer_journey_count < journey_count:
                    journey_type_name = next(journey_type_names)
                    key = make_key([journey_type_name, customer_profile.status])
                    if key not in journey_paths_index:
                        raise RuntimeError(u'No journey paths for %s.\nValid keys: %s' % (key, set(journey_paths_index)))
                    path, preferred_agent_from_path = next(journey_paths_index[key])
                    journey_type = journey_type_by_name[journey_type_name]
                    customer_journey_count += 1
                    yield journey_type, path, preferred_agent_from_path, customer_profile

        return gen_params

    def _create_journeys_with_paths(self, paths, customer_journey_counts, stick_to_paths=False):
        from solariat_bottle.scripts.data_load.gforce.customers import generate_customers, generate_agents
        from solariat_bottle.scripts.data_load.generate_gforce_demo import generate_journey_with_path, get_agent_profile_generators, get_template_generators

        agents = generate_agents(self.account.id)
        kwargs = {'agent_profile_generators': get_agent_profile_generators(self.account),
                  'template_generators': get_template_generators()}

        journey_params = self._setup_journey_params_generator(paths, stick_to_paths=stick_to_paths)

        for params in journey_params(customer_journey_counts):
            generate_journey_with_path(self.user, *params, **kwargs)
