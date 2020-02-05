import json
from datetime import datetime, timedelta

from solariat_bottle.tests.base import RestCase, setup_agent_schema
from solariat_bottle.api.agents import KEY_RETURN_OBJECTS
from solariat_bottle.db.channel.twitter import TwitterServiceChannel
from solariat_bottle.db.roles import ADMIN
from solariat_bottle.db.account import Account
from solariat_bottle.db.dynamic_profiles import FIELD_TOO_LONG

from solariat_bottle.db.schema_based import KEY_NAME, KEY_TYPE, TYPE_INTEGER


class TestApiAgentsBase(RestCase):

    def age_ag_1(self):
        birth_date = datetime(year=1985, month=6, day=6)
        delta = datetime.now() - birth_date
        return int(delta.days / 365.2425)

    def age_ag_2(self):
        birth_date = datetime(year=1981, month=7, day=7)
        delta = datetime.now() - birth_date
        return int(delta.days / 365.2425)

    def _create_edit_agent(self, token, skills, agent_id, name, date_of_hire, date_of_birth, gender, location,
                           extra_data=None, edit=False):
        happy_flow_data = {
            'name': name,
            'skills': skills,
            'date_of_birth': date_of_birth,
            'gender': gender,
            'location': location,
            'token': token,
            'native_id': agent_id,
            'date_of_hire': date_of_hire,
            'id': agent_id,
            KEY_RETURN_OBJECTS: True
        }
        if extra_data:
            happy_flow_data.update(extra_data)
        if edit:
            resp = self.client.put('/api/v2.0/agents',
                                   data=json.dumps(happy_flow_data),
                                   content_type='application/json',
                                   base_url='https://localhost')
        else:
            resp = self.client.post('/api/v2.0/agents',
                                    data=json.dumps(happy_flow_data),
                                    content_type='application/json',
                                    base_url='https://localhost')
        self.assertEqual(resp.status_code, 200, resp.data)
        post_data = json.loads(resp.data)
        self.assertTrue(post_data['ok'])
        return post_data['item']

    def create_agent(self, token, skills, native_id, name, date_of_hire, date_of_birth, gender, location,
                     extra_data=None):
        happy_flow_data = {
            'name': name,
            'skills': skills,
            'date_of_birth': date_of_birth,
            'gender': gender,
            'location': location,
            'token': token,
            'native_id': native_id,
            'date_of_hire': date_of_hire,
            'attached_data': extra_data,
            KEY_RETURN_OBJECTS: True
        }
        resp = self.client.post('/api/v2.0/agents',
                                data=json.dumps(happy_flow_data),
                                content_type='application/json',
                                base_url='https://localhost')
        self.assertEqual(resp.status_code, 200, resp.data)
        post_data = json.loads(resp.data)
        self.assertTrue(post_data['ok'])
        return post_data['item']

    def edit_agent(self, token, skills, agent_id, name, date_of_hire, date_of_birth, gender, location, native_id,
                   extra_data=None):
        happy_flow_data = {
            'name': name,
            'skills': skills,
            'date_of_birth': date_of_birth,
            'gender': gender,
            'location': location,
            'token': token,
            'native_id': native_id,
            'date_of_hire': date_of_hire,
            'id': agent_id,
            'attached_data': extra_data,
            KEY_RETURN_OBJECTS: True
        }
        resp = self.client.put('/api/v2.0/agents',
                               data=json.dumps(happy_flow_data),
                               content_type='application/json',
                               base_url='https://localhost')
        self.assertEqual(resp.status_code, 200, resp.data)
        post_data = json.loads(resp.data)
        self.assertTrue(post_data['ok'])
        return post_data['item']

    def delete_agent(self, token, agent_id):
        post_data = dict(token=token, id=agent_id)
        resp = self.client.delete('/api/v2.0/agents',
                                  data=json.dumps(post_data),
                                  content_type='application/json',
                                  base_url='https://localhost')
        data = json.loads(resp.data)
        return data['removed_count']

    def list_agents(self, token, filter_query=None, debug=False, extra_query=dict()):
        post_data = dict(token=token,
                         debug_query=debug)
        if filter:
            post_data['filter'] = filter_query
        if extra_query:
            post_data.update(extra_query)
        resp = self.client.get('/api/v2.0/agents',
                               data=json.dumps(post_data),
                               content_type='application/json',
                               base_url='https://localhost')
        data = json.loads(resp.data)
        return data['list'] if 'list' in data else [data['item']]

    def batch_create(self, token, batch):
        happy_flow_data = {'token': token,
                           'batch_data': batch,
                           KEY_RETURN_OBJECTS: True}
        resp = self.client.post('/api/v2.0/agents',
                                data=json.dumps(happy_flow_data),
                                content_type='application/json',
                                base_url='https://localhost')
        self.assertEqual(resp.status_code, 200, resp.data)
        post_data = json.loads(resp.data)
        self.assertTrue(post_data['ok'])
        return post_data['list']

    def batch_update(self, token, batch):
        happy_flow_data = {'token': token,
                           'batch_data': batch,
                           KEY_RETURN_OBJECTS: True}
        resp = self.client.put('/api/v2.0/agents',
                               data=json.dumps(happy_flow_data),
                               content_type='application/json',
                               base_url='https://localhost')
        self.assertEqual(resp.status_code, 200, resp.data)
        post_data = json.loads(resp.data)
        self.assertTrue(post_data['ok'])
        return post_data

    def setup_requirements(self, email, password, extra_schema=[], skip_schema=False):
        new_account = Account.objects.create(name='TestAccount1')
        admin_user = self._create_db_user(email=email,
                                          password=password,
                                          roles=[ADMIN])
        new_account.add_perm(admin_user)
        admin_user.account = new_account
        admin_user.save()
        TwitterServiceChannel.objects.create_by_user(admin_user, title='TSC')
        if not skip_schema:
            setup_agent_schema(admin_user, extra_schema)
        return admin_user


class TestApiAgents(TestApiAgentsBase):

    def test_no_schema(self):
        user_mail = 'admin1@test_channels.com'
        user_password = 'password'
        user = self.setup_requirements(user_mail, user_password, skip_schema=True)
        token = self.get_token(user_mail, user_password)
        agent_one = self.create_agent(token=token,
                                      #skills=dict(products=7, sales=5),
                                      skills={u"products": 7, u"sales": 5, u"dot.products": 7, u"multi.dots.sales": 5},
                                      name="Tester Testerson",
                                      date_of_hire="01/01/2001",
                                      date_of_birth="06/06/1985",
                                      native_id='agent_one',
                                      gender="M",
                                      location="San Francisco",
                                      extra_data={'test': 1, 'test2': 2})
        agents_list = self.list_agents(token)
        for agent in agents_list:
            agent.pop('id')
        self.assertEqual(len(agents_list), 1)
        expected_agents = [{u'name': u'Tester Testerson',
                            u'gender': u'M',
                            u'native_id': u'agent_one',
                            u'location': u'San Francisco',
                            u'skills': {u'products': 7, u'sales': 5, u'dot.products': 7, u'multi.dots.sales': 5},
                            u'attached_data': {u'test': 1,
                                               u'test2': 2},
                            u'linked_profile_ids': [],
                            u'account_id': str(user.account.id),
                            u'date_of_birth': u'06/06/1985',
                            u'date_of_hire': u'01/01/2001',
                            },]
        self.assertListEqual(agents_list, expected_agents)

        agent_schema = user.account.agent_profile._get()
        for key in [u'name', u'skills', u'gender', u'attached_data', u'native_id', u'date_of_birth',
                    u'location', u'date_of_hire']:
            self.assertTrue(key in agent_schema.cardinalities and agent_schema.cardinalities[key]['count'] == 1)

    def test_no_refresh_cardinalities_twice(self):
        user_mail = 'admin1@test_channels.com'
        user_password = 'password'
        user = self.setup_requirements(user_mail, user_password, skip_schema=True)
        token = self.get_token(user_mail, user_password)
        agent_one = self.create_agent(token=token,
                                      # skills=dict(products=7, sales=5),
                                      skills={u"products": 7, u"sales": 5,
                                              u"dot.products": 7, u"multi.dots.sales": 5},
                                      name="Tester Testerson",
                                      date_of_hire="01/01/2001",
                                      date_of_birth="06/06/1985",
                                      native_id='agent_one',
                                      gender="M",
                                      location="San Francisco",
                                      extra_data={'test': 1, 'test2': 2})
        agents_list = self.list_agents(token)
        for agent in agents_list:
            agent.pop('id')
        self.assertEqual(len(agents_list), 1)
        expected_agents = [{u'name': u'Tester Testerson',
                            u'gender': u'M',
                            u'native_id': u'agent_one',
                            u'location': u'San Francisco',
                            u'skills': {u'products': 7, u'sales': 5, u'dot.products': 7, u'multi.dots.sales': 5},
                            u'attached_data': {u'test': 1,
                                               u'test2': 2},
                            u'linked_profile_ids': [],
                            u'account_id': str(user.account.id),
                            u'date_of_birth': u'06/06/1985',
                            u'date_of_hire': u'01/01/2001',
                            }, ]
        self.assertListEqual(agents_list, expected_agents)

        agent_schema = user.account.agent_profile._get()
        for key in [u'name', u'skills', u'gender', u'attached_data', u'native_id', u'date_of_birth',
                    u'location', u'date_of_hire']:
            self.assertTrue(key in agent_schema.cardinalities and agent_schema.cardinalities[key]['count'] == 1)
        agent_two = self.create_agent(token=token,
                                      # skills=dict(products=7, sales=5),
                                      skills={u"products": 7, u"sales": 5,
                                              u"dot.products": 7, u"multi.dots.sales": 5},
                                      name="Tester Testerson1",
                                      date_of_hire="01/01/2002",
                                      date_of_birth="06/06/1986",
                                      native_id='agent_two',
                                      gender="M2",
                                      location="San Francisco2",
                                      extra_data={'test1': 1, 'test3': 2})
        agents_list = self.list_agents(token)
        for agent in agents_list:
            agent.pop('id')
        self.assertEqual(len(agents_list), 2)
        agent_schema = user.account.agent_profile._get()
        for key in [u'name', u'skills', u'gender', u'attached_data', u'native_id', u'date_of_birth',
                    u'location', u'date_of_hire']:
            self.assertTrue(key in agent_schema.cardinalities and agent_schema.cardinalities[key]['count'] == 1)
        agent_schema.cardinalities_lu = datetime.now() - timedelta(hours=4)
        agent_schema.save()
        agent_two = self.create_agent(token=token,
                                      # skills=dict(products=7, sales=5),
                                      skills={u"products": 7, u"sales": 5,
                                              u"dot.products": 7, u"multi.dots.sales": 5},
                                      name="Tester Testerson3",
                                      date_of_hire="01/01/2003",
                                      date_of_birth="06/06/1987",
                                      native_id='agent_three',
                                      gender="F",
                                      location="San Francisco",
                                      extra_data={'test2': 1, 'test3': 2})
        agents_list = self.list_agents(token)
        for agent in agents_list:
            agent.pop('id')
        self.assertEqual(len(agents_list), 3)
        agent_schema = user.account.agent_profile._get()
        for key in [u'name', u'skills', u'gender', u'attached_data', u'native_id', u'date_of_birth',
                    u'location', u'date_of_hire']:
            if key != 'skills':
                if key == 'location':
                    self.assertTrue(key in agent_schema.cardinalities and agent_schema.cardinalities[key]['count'] == 2)
                else:
                    self.assertTrue(key in agent_schema.cardinalities and agent_schema.cardinalities[key]['count'] == 3)

    def test_indexes_created(self):
        user_mail = 'admin1@test_channels.com'
        user_password = 'password'
        user = self.setup_requirements(user_mail, user_password, skip_schema=True)
        token = self.get_token(user_mail, user_password)
        agent_one = self.create_agent(token=token,
                                      # skills=dict(products=7, sales=5),
                                      skills={u"products": 7, u"sales": 5,
                                              u"dot.products": 7, u"multi.dots.sales": 5},
                                      name="Tester Testerson",
                                      date_of_hire="01/01/2001",
                                      date_of_birth="06/06/1985",
                                      native_id='agent_one',
                                      gender="M",
                                      location="San Francisco",
                                      extra_data={'test': 1, 'test2': 2})
        agents_list = self.list_agents(token)
        for agent in agents_list:
            agent.pop('id')
        self.assertEqual(len(agents_list), 1)
        agent_schema = user.account.agent_profile._get()
        AgentProfile = agent_schema.get_data_class()
        self.assertEqual(len(AgentProfile.objects.coll.index_information()), 9)

    def test_agents_crud_schema_enforced(self):
        user_mail = 'admin1@test_channels.com'
        user_password = 'password'
        user = self.setup_requirements(user_mail, user_password, extra_schema=[{
                                                                                   KEY_NAME: 'NUMERIC',
                                                                                   KEY_TYPE: TYPE_INTEGER,
                                                                               }])
        token = self.get_token(user_mail, user_password)
        batch_data = [dict(token=token,
                           # skills=dict(products=7, sales=5),
                           skills={u"products": 7, u"sales": 5, u"dot.products": 7, u"multi.dots.sales": 5},
                           name="Tester Testerson",
                           date_of_hire="01/01/2001",
                           date_of_birth="06/06/1985",
                           native_id='agent_one',
                           gender="M",
                           location="San Francisco" * 20,
                           extra_data="{'test': 1, 'test2': 2}",
                           NUMERIC='asd'),
                      dict(token=token,
                           # skills=dict(products=7, sales=5),
                           skills='{u"products": 6, u"sales": 3, u"dot.products": 5, u"multi.dots.sales": 4}',
                           name="Tester1 Testerson1",
                           date_of_hire="01/02/2001",
                           date_of_birth="06/07/1985",
                           native_id='agent_two',
                           gender="F",
                           location="San Jose",
                           extra_data="{'test': 1, 'test2': 2}",
                           NUMERIC='123')]
        self.batch_create(token, batch_data)
        agents_list = self.list_agents(token)
        for entry in agents_list:
            self.assertTrue(isinstance(entry['skills'], dict))
            if entry['gender'] == 'F':
                self.assertTrue(entry['NUMERIC'] == 123)
            else:
                self.assertTrue(entry['NUMERIC'] is None)   # 'asd' invalid numeric, will be skipped
                self.assertEqual(entry['location'], FIELD_TOO_LONG)

    def test_agents_no_schema_native_id(self):
        user_mail = 'admin1@test_channels.com'
        user_password = 'password'
        user = self.setup_requirements(user_mail, user_password, skip_schema=True)
        token = self.get_token(user_mail, user_password)
        agent_one = self.create_agent(token=token,
                                      #skills=dict(products=7, sales=5),
                                      skills= {u"products": 7, u"sales": 5, u"dot.products": 7, u"multi.dots.sales": 5},
                                      name="Tester Testerson",
                                      date_of_hire="01/01/2001",
                                      date_of_birth="06/06/1985",
                                      native_id='agent_one',
                                      gender="M",
                                      location="San Francisco",
                                      extra_data={'test': 1, 'test2': 2})
        agents_list = self.list_agents(token, extra_query=dict(native_id='agent_one'))
        for agent in agents_list:
            agent.pop('id')
        self.assertEqual(len(agents_list), 1)
        expected_agents = [{u'name': u'Tester Testerson',
                            u'gender': u'M',
                            u'native_id': u'agent_one',
                            u'location': u'San Francisco',
                            u'skills': {u'products': 7, u'sales': 5, u'dot.products': 7, u'multi.dots.sales': 5},
                            u'attached_data': {u'test': 1,
                                               u'test2': 2},
                            u'linked_profile_ids': [],
                            u'account_id': str(user.account.id),
                            u'date_of_birth': u'06/06/1985',
                            u'date_of_hire': u'01/01/2001',
                            },]
        self.assertListEqual(agents_list, expected_agents)

    def test_agents_crud(self):
        user_mail = 'admin1@test_channels.com'
        user_password = 'password'
        user = self.setup_requirements(user_mail, user_password)
        token = self.get_token(user_mail, user_password)
        agent_one = self.create_agent(token=token,
                                      #skills=dict(products=7, sales=5),
                                      skills= {u"products": 7, u"sales": 5, u"dot.products": 7, u"multi.dots.sales": 5},
                                      name="Tester Testerson",
                                      date_of_hire="01/01/2001",
                                      date_of_birth="06/06/1985",
                                      native_id='agent_one',
                                      gender="M",
                                      location="San Francisco",
                                      extra_data={'test':1, 'test2':2})
        agent_two = self.create_agent(token=token,
                                      skills=dict(products=3, sales=10),
                                      name="Badboy Agent",
                                      date_of_hire="04/04/2004",
                                      native_id='agent_two',
                                      date_of_birth="07/7/1981",
                                      gender="M",
                                      location="San Francisco")

        agents_list = self.list_agents(token)
        self.assertEqual(len(agents_list), 2)
        agent_ids = []
        for agent in agents_list:
            agent_ids.append(agent.pop('id'))

        expected_agents = [{u'name': u'Tester Testerson',
                            u'gender': u'M',
                            u'native_id': u'agent_one',
                            u'location': u'San Francisco',
                            u'on_call': None,
                            u'skills': {u'products': 7, u'sales': 5, u'dot.products': 7, u'multi.dots.sales': 5},
                            u'attached_data': {u'test': 1,
                                               u'test2': 2},
                            u'linked_profile_ids': [],
                            u'account_id': str(user.account.id),
                            u'date_of_birth': u'06/06/1985',
                            u'date_of_hire': u'01/01/2001',
                            # u'test': 1,
                            # u'test2': 2
                            },
                           {u'name': u'Badboy Agent',
                            u'gender': u'M',
                            u'native_id': u'agent_two',
                            u'on_call': None,
                            u'location': u'San Francisco',
                            u'skills': {u'products': 3, u'sales': 10},
                            u'attached_data': None,
                            u'linked_profile_ids': [],
                            u'account_id': str(user.account.id),
                            u'date_of_birth': u'07/7/1981',
                            u'date_of_hire': u'04/04/2004'}]
        self.assertListEqual(agents_list, expected_agents)

        self.edit_agent(token=token,
                        skills=dict(products=3, sales=10),
                        agent_id=agent_ids[1],
                        name="Sadboy Agent",
                        date_of_hire="04/04/2004",
                        date_of_birth="07/7/1981",
                        gender="M",
                        native_id='agent_two',
                        location="San Francisco")
        agents_list = self.list_agents(token)
        self.assertEqual(len(agents_list), 2)
        agent_ids = []
        for agent in agents_list:
            agent_ids.append(agent.pop('id'))

        expected_agents = [{u'name': u'Tester Testerson',
                            u'gender': u'M',
                            u'native_id': u'agent_one',
                            u'location': u'San Francisco',
                            u'on_call': None,
                            u'skills': {u'products': 7, u'sales': 5, u'dot.products': 7, u'multi.dots.sales': 5},
                            u'attached_data': {u'test': 1,
                                               u'test2': 2},
                            u'linked_profile_ids': [],
                            u'account_id': str(user.account.id),
                            u'date_of_birth': u'06/06/1985',
                            u'date_of_hire': u'01/01/2001'},
                           {u'name': u'Sadboy Agent',
                            u'gender': u'M',
                            u'native_id': u'agent_two',
                            u'on_call': None,
                            u'location': u'San Francisco',
                            u'skills': {u'products': 3, u'sales': 10},
                            u'attached_data': None,
                            u'linked_profile_ids': [],
                            u'account_id': str(user.account.id),
                            u'date_of_birth': u'07/7/1981',
                            u'date_of_hire': u'04/04/2004'}]
        self.assertListEqual(agents_list, expected_agents)

        removed_count = self.delete_agent(token, agent_ids[0])
        self.assertEqual(removed_count, 1)

        agents_list = self.list_agents(token)
        agent_ids = []
        for agent in agents_list:
            agent_ids.append(agent.pop('id'))
        expected_agents = [{u'name': u'Sadboy Agent',
                            u'gender': u'M',
                            u'native_id': u'agent_two',
                            u'location': u'San Francisco',
                            u'on_call': None,
                            u'skills': {u'products': 3, u'sales': 10},
                            u'attached_data': None,
                            u'linked_profile_ids': [],
                            u'account_id': str(user.account.id),
                            u'date_of_birth': u'07/7/1981',
                            u'date_of_hire': u'04/04/2004'}]

        self.assertEqual(len(agents_list), 1)
        self.assertListEqual(agents_list, expected_agents)

    def test_batch_crud(self):
        user_mail = 'admin1@test_channels.com'
        user_password = 'password'
        user = self.setup_requirements(user_mail, user_password)
        token = self.get_token(user_mail, user_password)
        batch_data = [{u'name': u'Tester Testerson',
                       u'gender': u'M',
                       u'date_of_birth': u'06/06/1985',
                       u'date_of_hire': u'01/01/2001',
                       u'native_id': u'UUID_1',
                       u'location': u'San Francisco',
                       u'skills': {},
                       u'test': 1,
                       u'on_call': False,
                       u'test2': 2},
                      {u'name': u'Badboy Agent',
                       u'gender': u'M',
                       u'date_of_birth': u'07/7/1981',
                       u'date_of_hire': u'04/04/2004',
                       u'native_id': u'UUID_2',
                       u'on_call': False,
                       u'location': u'San Francisco',
                       u'skills': {}},
                      {u'location': u'',
                       u'attached_data': {u'EN_VO': 25,
                                          u'ROG_CXCARE_PPD': 30,
                                          u'loginCodes': [u'20110'],
                                          u'userName': u'T020110',
                                          u'employeeId': u'T020110',
                                          u'firstName': u'Agent 20110',
                                          u'interaction-workspace': {u'spellchecker.personal-dictionary': u'',
                                                                     u'login.MKH_AVAYA.voice.1.dn-isselected': u'True',
                                                                     u'login.MKH_AVAYA.voice.1.dn-queue': u'',
                                                                     u'login.MKH_AVAYA.voice.1.dn-agent-login': u'20114'},
                                          u'multimedia': {u'last-media-logged': u'[voice]@MKH_AVAYA,outboundpreview'},
                                          u'dbID': 77133,
                                          u'state': u'CFGEnabled',
                                          u'tenantName': u'Resources',
                                          u'loginStatus': -1,
                                          u'lastName': u'Preprod Avaya',
                                          u'tenantDbID': 101,
                                          u'AVA': 1,
                                          u'loginId': u''},
                       u'sex': u'',
                       u'skills': {u'EN_VO': 25,
                                   u'AVA': 1,
                                   u'ROG_CXCARE_PPD': 30},
                       u'native_id': u'77133',
                       u'date_of_birth': u'',
                       u'date_of_hire': u'',
                       u'on_call': False
                      }]
        self.batch_create(token, batch_data)
        agents_list = self.list_agents(token)
        agent_ids = []
        for agent in agents_list:
            agent_ids.append(agent.pop('id'))

        expected_data = [{u'name': u'Tester Testerson',
                          u'skills': {},
                          u'gender': u'M',
                          u'attached_data': {},
                          u'location': u'San Francisco',
                          u'date_of_birth': u'06/06/1985',
                          u'date_of_hire': u'01/01/2001',
                          u'native_id': u'UUID_1',
                          u'linked_profile_ids': [],
                          u'sex': None,
                          u'account_id': str(user.account.id),
                          u'test': 1,
                          u'test2': 2,
                          u'on_call': False},
                         {u'name': u'Badboy Agent',
                          u'skills': {},
                          u'gender': u'M',
                          u'attached_data': {},
                          u'on_call': False,
                          u'location': u'San Francisco',
                          u'native_id': u'UUID_2',
                          u'sex': None,
                          u'test': None,
                          u'test2': None,
                          u'linked_profile_ids': [],
                          u'account_id': str(user.account.id),
                          u'date_of_birth': u'07/7/1981',
                          u'date_of_hire': u'04/04/2004',},
                         {u'name': None,
                          u'skills': {u'EN_VO': 25, u'AVA': 1, u'ROG_CXCARE_PPD': 30},
                          u'gender': None,
                          u'linked_profile_ids': [],
                          u'date_of_birth': u'',
                          u'date_of_hire': u'',
                          u'sex': u'',
                          u'test': None,
                          u'test2': None,
                          u'account_id': str(user.account.id),
                          u'attached_data': FIELD_TOO_LONG,
                          u'native_id': u'77133',
                          u'location': u'',
                          u'on_call': False}
                         ]

        self.assertEqual(len(agents_list), 3)
        self.assertListEqual(agents_list, expected_data)

        batch_data = [{u'name': u'Tester Testerson',
                       u'gender': u'M',
                       u'date_of_birth': u'06/06/1985',
                       u'date_of_hire': u'01/01/2001',
                       u'native_id': u'UUID_1',
                       u'location': u'San Jose',
                       u'skills': {u'products': 7, u'sales': 5, u'dot.products': 7, u'multi.dots.sales': 5},
                       u'test': 1,
                       u'id': agent_ids[0],
                       u'test2': 2},
                      {u'name': u'Sadboy Agent',
                       u'gender': u'M',
                       u'date_of_birth': u'07/7/1981',
                       u'date_of_hire': u'04/04/2004',
                       u'native_id': u'UUID_2',
                       u'id': agent_ids[1],
                       u'location': u'San Francisco',
                       u'skills': {u'products': 3, u'sales': 10}}]
        self.batch_update(token, batch_data)

        expected_data = [{u'name': u'Tester Testerson',
                          u'skills': {u'products': 7, u'sales': 5, u'dot.products': 7, u'multi.dots.sales': 5},
                          u'gender': u'M',
                          u'attached_data': {},
                          u'location': u'San Jose',
                          u'native_id': u'UUID_1',
                          u'on_call': False,
                          u'linked_profile_ids': [],
                          u'account_id': str(user.account.id),
                          u'test': 1,
                          u'test2': 2,
                          u'sex': None,
                          u'date_of_birth': u'06/06/1985',
                          u'date_of_hire': u'01/01/2001'},
                         {u'name': u'Sadboy Agent',
                          u'skills': {u'products': 3, u'sales': 10},
                          u'gender': u'M',
                          u'attached_data': {},
                          u'test': None,
                          u'test2': None,
                          u'sex': None,
                          u'location': u'San Francisco',
                          u'native_id': u'UUID_2',
                          u'on_call': False,
                          u'linked_profile_ids': [],
                          u'account_id': str(user.account.id),
                          u'date_of_birth': u'07/7/1981',
                          u'date_of_hire': u'04/04/2004',},
                         {u'name': None,
                          u'skills': {u'EN_VO': 25, u'AVA': 1, u'ROG_CXCARE_PPD': 30},
                          u'gender': None,
                          u'linked_profile_ids': [],
                          u'date_of_birth': u'',
                          u'date_of_hire': u'',
                          u'test': None,
                          u'test2': None,
                          u'sex': u'',
                          u'account_id': str(user.account.id),
                          u'attached_data': FIELD_TOO_LONG,
                          u'native_id': u'77133',
                          u'location': u'',
                          u'on_call': False}
                         ]
        agents_list = self.list_agents(token)
        self.assertEqual(len(agents_list), 3)
        agent_ids = []
        for agent in agents_list:
            agent_ids.append(agent.pop('id'))
        self.assertListEqual(sorted(agents_list, key=lambda x: x['name']),
                             sorted(expected_data, key=lambda x: x['name']))

    def test_fetch_filter_based(self):
        user_mail = 'admin1@test_channels.com'
        user_password = 'password'
        self.setup_requirements(user_mail, user_password, extra_schema=[{
                                                                            KEY_NAME: 'FIELD',
                                                                            KEY_TYPE: TYPE_INTEGER,
                                                                            # KEY_EXPRESSION: 'name',
                                                                        },
                                                                        {
                                                                            KEY_NAME: 'SKILL',
                                                                            KEY_TYPE: TYPE_INTEGER,
                                                                            # KEY_EXPRESSION: 'name',
                                                                        }])
        token = self.get_token(user_mail, user_password)
        batch_data = [{u'name': u'Tester Testerson',
                       u'gender': u'M',
                       u'date_of_birth': u'06/06/1985',
                       u'date_of_hire': u'01/01/2001',
                       u'native_id': u'UUID_1',
                       u'location': u'San Francisco',
                       u'skills': {u'products': 7, u'hardware': 5},
                       u'attached_data': {u"FIELD": 1,
                                          u"SKILL": 1},
                       u"FIELD": 1,
                       u"SKILL": 1,
                       u'test': 1,
                       u'test2': 2},
                      {u'name': u'Badboy Agent',
                       u'gender': u'M',
                       u'date_of_birth': u'07/7/1981',
                       u'date_of_hire': u'04/04/2004',
                       u'native_id': u'UUID_2',
                       u'attached_data': {u"FIELD": 1,
                                          u"SKILL": 2,
                                          u"FIELD.WITH.DOTS": 3,
                                          u"another.dotted.field": 4},
                       u"FIELD": 1,
                       u"SKILL": 2,
                       u'location': u'San Francisco',
                       #u'skills': {u'products': 3, u'hr': 10, u'dotted.skill': 11}},
                       u'skills': {u'products': 3, u'hr': 10}},
                      {u'name': u'Sadboy Agent',
                       u'gender': u'M',
                       u'date_of_birth': u'07/7/1982',
                       u'date_of_hire': u'04/04/2005',
                       u'native_id': u'UUID_3',
                       u"FIELD": 2,
                       u'attached_data': {u"FIELD": 2},
                       u'location': u'San Jose',
                       u'skills': {u'products': 3, u'hardware': 10}}]
        self.batch_create(token, batch_data)

        # Simple query based on a simple field
        agents_list = self.list_agents(token, filter_query='FIELD=1')
        native_ids = []
        # Only first two should be matched
        for agent in agents_list:
            native_ids.append(agent.pop('native_id'))
        self.assertEqual(set(native_ids), set([u'UUID_1', u'UUID_2']))

        agents_list = self.list_agents(token, filter_query='FIELD=1& SKILL=2')
        native_ids = []
        # Only first two should be matched
        for agent in agents_list:
            native_ids.append(agent.pop('native_id'))
        self.assertEqual(set(native_ids), set([u'UUID_2']))

        new_field_agent = [{u'name': u'Sadboy2 Agent',
                           u'gender': u'M',
                           u'date_of_birth': u'07/7/1982',
                           u'date_of_hire': u'04/04/2005',
                           u'native_id': u'UUID_4',
                           u"FIELD": 2,
                           u'location': u'San Jose',
                           u'skills': {u'products': 3, u'hardware': 10},
                           u'FIELD_NEW': 1}]
        self.batch_create(token, new_field_agent)
        agents_list = self.list_agents(token, filter_query='FIELD_NEW=1')
        self.assertEqual(len(agents_list), 1)

    def test_agent_availability_switch(self):
        user_mail = 'admin1@test_channels.com'
        user_password = 'password'
        self.setup_requirements(user_mail, user_password)
        token = self.get_token(user_mail, user_password)
        batch_data = [{u'name': u'Tester Testerson',
                       u'gender': u'M',
                       u'date_of_birth': u'06/06/1985',
                       u'date_of_hire': u'01/01/2001',
                       u'native_id': u'UUID_1',
                       u'location': u'San Francisco',
                       u'skills': {u'products': 7, u'hardware': 5},
                       u'test': 1,
                       u'test2': 2},
                      {u'name': u'Badboy Agent',
                       u'gender': u'M',
                       u'date_of_birth': u'07/7/1981',
                       u'date_of_hire': u'04/04/2004',
                       u'native_id': u'UUID_2',
                       u'location': u'San Francisco',
                       u'skills': {u'products': 3, u'hr': 10}},
                      {u'name': u'Sadboy Agent',
                       u'gender': u'M',
                       u'date_of_birth': u'07/7/1982',
                       u'date_of_hire': u'04/04/2005',
                       u'native_id': u'UUID_3',
                       u'location': u'San Jose',
                       u'skills': {u'products': 3, u'hardware': 10}}]
        self.batch_create(token, batch_data)

        agents_list = self.list_agents(token)
        self.assertEqual(len(agents_list), 3)
        agent_ids = []
        agent_native_ids = []
        for agent in agents_list:
            agent_ids.append(agent.pop('id'))
            agent_native_ids.append(agent.pop('native_id'))

        LOGIN_STATUS = 23 # constant from URS
        happy_flow_data = {'token': token,
                           'batch_data': json.dumps({
                             'agent_list': agent_native_ids,
                             'login_status': LOGIN_STATUS})}

        resp = self.client.post('/api/v2.0/agents/loginstatus',
                                data=json.dumps(happy_flow_data),
                                content_type='application/json',
                                base_url='https://localhost')
        self.assertEqual(resp.status_code, 200, resp.data)

        agents_list = self.list_agents(token)
        self.assertEqual(len(agents_list), 3)
        self.assertEqual(
            [x.get('attached_data', {}).get('loginStatus') for x in agents_list], 
            [LOGIN_STATUS]*3
        )


