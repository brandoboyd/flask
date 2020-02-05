import json

from bson import ObjectId
from solariat.db.abstract import DBRef

from pymongo import TEXT
from sklearn.feature_extraction.text import HashingVectorizer

from solariat.db import fields

from solariat_nlp import search
from solariat_nlp.filter_cls.classifier import FilterClassifier
from solariat_nlp.search.base import SearchEngineBase
from solariat_nlp.search.es import FAQCollection, SE1

from solariat_bottle.settings import LOGGER
from solariat_bottle.db.auth import ArchivingAuthDocument, ArchivingAuthManager
from solariat_bottle.db.roles import ADMIN, STAFF
from solariat_bottle.db.channel.base import Channel

MAX_FIELD_WEIGHT = 2.0


class DbBasedSE1(SE1):

    def __init__(self, channel):
        self.channel = channel
        self.faqs = []
        self._doc_info = None
        # self.set_mapping()

    @property
    def doc_info(self):
        if self._doc_info is None:
            try:
                self._doc_info = FAQDocumentInfo.objects.get(channel=self.channel)
            except FAQDocumentInfo.DoesNotExist:
                self.compile_faqs()
                self._doc_info = FAQDocumentInfo.objects.get(channel=self.channel)
        return self._doc_info

    def __get_answer_df(self):
        return self.doc_info.answer_df

    def __set_answer_df(self, answer_df):
        self.doc_info.answer_df = answer_df
        self.doc_info.save()

    answer_df = property(__get_answer_df, __set_answer_df)

    def __get_query_df(self):
        return self.doc_info.query_df

    def __set_query_df(self, query_df):
        self.doc_info.query_df = query_df
        self.doc_info.save()

    query_df = property(__get_query_df, __set_query_df)

    def __get_stemmer(self):
        return self.doc_info.stemmer

    def __set_stemmer(self, stemmer):
        self.doc_info.stemmer = stemmer
        self.doc_info.save()

    stemmer = property(__get_stemmer, __set_stemmer)

    def __get_query_count(self):
        return self.doc_info.query_count

    def __set_query_count(self, query_count):
        self.doc_info.query_count = query_count
        self.doc_info.save()

    query_count = property(__get_query_count, __set_query_count)

    def prepare_es_query(self, query):
        es_base_query = super(DbBasedSE1, self).prepare_es_query(query)
        enhanced_query = {
            'filter': {"and": [{"terms": {"channels": [str(self.channel.id)]}}]},
            'query': es_base_query
        }
        es_query = {'filtered': enhanced_query}
        return es_query

    def execute_search(self, query, limit):
        results = super(DbBasedSE1, self).execute_search(query, limit)
        valid_results = []
        for entry in results:
            try:
                FAQ.objects.get(entry['id'])
                valid_results.append(entry)
            except FAQ.DoesNotExist:
                LOGGER.warning("Removed FAQ stall entry from ES: " + str(entry['id']))
                self.collection.delete(str(entry['id']))
        # Removing normalization because it introduces strange biases into the data for
        # or agsint ES. It implicitly limits the impact of ES on the search.
        #max_score = max([r['relevance'] for r in valid_results])
        #for result in valid_results:
        #    result['relevance'] = result['relevance'] / max_score
        return valid_results

    def search(self, query, limit):
        search_results = super(DbBasedSE1, self).search(query, limit)
        # search_results =  self.doc_info.objects.find(**{'$text': {'$search': query}, 'channel': channel})[:]
        # search_results =  self.doc_info.objects.find(**{'$text': {'$search': query}})[:]
        results = [{'relevance': res['relevance'],
                    'answer': res['answer'],
                    'question': res['question'],
                    'id': res['id']} for res in search_results]
        return results

    def score(self, query_vec, faq):
        """
        Ideas:
        1. Use a passive aggressive algorithm to integrate feedback
        2. Retain the simple vector union model so we can learn something
        3. Use prediction from PA algorithm to rank the top K
        4. Combine the BM25 score:
        * With no feedback it should give no weighting.
        * More balanced feedback should improve the trust of the score
        * Maintain a low dimensional vector space
        * Capture positive and negative feedback

        On the score:

        SCORE = BM2F(q, f) * ( w + pa_score(q, f))
        """
        faq_object = FAQ.objects.get(faq['id'])
        if not faq_object.feedback:
            return faq['relevance']
        return faq['relevance'] * faq_object.clf.score(query_vec)

    def train(self, faq_id, query, is_relevant=True):
        faq = FAQ.objects.get(faq_id)
        faq.train(query, is_relevant)

    def compile_faqs(self):
        """
        Compile all the faqs for this channel in a document holding all the info for quick retrieval later on.
        """
        def doc_to_dict(faq):
            return dict(answer=faq.answer,
                        question=faq.question,
                        queries=faq.queries)
        self.faqs = [doc_to_dict(faq) for faq in FAQ.objects.find(channel=self.channel)]
        answer_df, query_df, stemmer, query_count = search.compile_faqs(self.faqs)
        try:
            doc_info = FAQDocumentInfo.objects.get(channel=self.channel)
        except FAQDocumentInfo.DoesNotExist:
            doc_info = FAQDocumentInfo.objects.create(channel=self.channel)
        doc_info.answer_df = answer_df
        doc_info.query_df = query_df
        doc_info.stemmer = stemmer
        doc_info.query_count = query_count
        doc_info.save()

class FAQManager(ArchivingAuthManager, SearchEngineBase):

    def create(self, channel, **kw):
        ''' Automatically deploy for matching once created '''
        faq = ArchivingAuthManager.create(self, channel=channel, **kw)
        DbBasedSE1(channel).compile_faqs()
        faq.process_queries()
        # if faq.is_active:
        #     faq.put_to_es()
        return faq

    def create_by_user(self, user, channel, **kw):
        faq = ArchivingAuthManager.create_by_user(self, user, channel=channel, **kw)
        DbBasedSE1(channel).compile_faqs()
        faq.process_queries()
        # if faq.is_active:
        #     faq.put_to_es()
        return faq

    def remove_by_user(self, user, *args, **kw):
        if args:
            kw = {'id': args[0]}
        for faq in ArchivingAuthManager.find_by_user(self, user, 'w', **kw):
            faq.is_archived = True
            faq.is_active = False
            faq.save()
            self.model.es_collection.delete(str(faq.id))
        # self.model.es_collection.index.refresh()

    def withdraw(self, *args, **kw):
        'Remove matchable from active deployment. Will extract from ES.'
        for faq in self.find(*args, **kw):
            faq.withdraw()
        self.model.es_collection.index.refresh()

    def text_search(self, channel, search_text, limit=100):
        channel = str(channel.id) if isinstance(channel, Channel) else str(channel)
        if search_text:
            channel_dbref = DBRef('Channel', ObjectId(channel))
            results = (self.coll.find(
                    {'$text': {'$search': search_text}, 'channel': channel_dbref, 'is_archived': False}, 
                    {'score': {'$meta': "textScore"}}
                )
                .sort([('score', {'$meta': 'textScore'})])
                .limit(limit) )
            results = [x for x in results]
            results = [ {
                    'relevance': x['score'],
                    'answer': x['a'],
                    'question': x['q'],
                    'id': str(x['_id'])
                } for x in results ]
            faqs = FAQ.objects.find(id__in=[x['id'] for x in results])
            faqs = {str(x.id): x for x in faqs}
            for i in range(len(results)):
                faq_object = faqs.get(results[i]['id'])
                query_vec = DbBasedSE1.translate(search_text)
                score = faq_object.clf.score(query_vec) if faq_object else 1
                results[i]['relevance'] *= score
        else:
            results = self.find(**{'channel': channel, 'is_archived': False}).limit(limit)[:]
            results = [ {
                'relevance': 0.1, # let it be a default score
                'answer': x.answer,
                'question': x.question,
                'id': str(x.id)
            } for x in results ]
        return results


class FAQDocumentInfo(ArchivingAuthDocument):
    collection = 'FAQDocInfo'

    channel = fields.ReferenceField('Channel', db_field='ch')
    _answer_df = fields.StringField()
    _query_df = fields.StringField()
    _stemmer = fields.StringField()
    query_count = fields.NumField()

    indexes = [('channel'), ]
    # indexes = [('channel'), (('_query_df', TEXT), None, 'english')]

    def __get_answer_df(self):
        return json.loads(self._answer_df)

    def __set_answer_df(self, answer_df):
        self._answer_df = json.dumps(answer_df)

    answer_df = property(__get_answer_df, __set_answer_df)

    def __get_query_df(self):
        return json.loads(self._query_df)

    def __set_query_df(self, query_df):
        self._query_df = json.dumps(query_df)

    query_df = property(__get_query_df, __set_query_df)

    def __get_stemmer(self):
        return json.loads(self._stemmer)

    def __set_stemmer(self, stemmer):
        self._stemmer = json.dumps(stemmer)

    stemmer = property(__get_stemmer, __set_stemmer)


class FAQ(ArchivingAuthDocument):
    "This is the customer message we search for"
    collection = 'FAQ'

    allow_inheritance = True
    manager = FAQManager

    channel = fields.ReferenceField('Channel')
    question = fields.StringField(db_field='q')
    answer = fields.StringField(db_field='a')
    queries = fields.ListField(fields.StringField())
    feedback = fields.ListField(fields.DictField(), db_field='f')
    packed_clf = fields.BinaryField(db_field='clf')

    is_active = fields.BooleanField(default=True, db_field='ia')

    indexes = [('channel'), ]
    
    admin_roles = [ADMIN, STAFF]
    relevance = 0
    vector = {}

    @property
    def classifier_class(self):
        "So we can easily plugin other classifier classes if we want."
        return FilterClassifier

    @property
    def clf(self):
        def extract(s):
            return s

        if not hasattr(self, '_clf') or not self._clf:
            if self.packed_clf:
                self._clf = FilterClassifier(model=self.packed_clf)
            else:
                self._clf = FilterClassifier()
        self._clf.extract_features = extract
        self._clf.__vectorizer = HashingVectorizer(n_features=20,
                                                   lowercase=True,
                                                   binary=True)
        return self._clf

    def process_queries(self):
        for query in self.queries:
            self.train(query, True)

    def save(self, update_es=False):
        self.packed_clf = self.clf.packed_model
        super(FAQ, self).save()
        if update_es:
            self.put_to_es(refresh=True)

    def delete(self):
        super(FAQ, self).delete()
        # self.es_collection.delete(str(self.id))
        # self.es_collection.index.refresh()
        DbBasedSE1(self.channel).compile_faqs()

    def train(self, query, is_relevant):
        assert is_relevant <= 1, "GOT FEEDBACK WITH SCORE " + str(is_relevant)
        self.feedback.append(dict(query=query, is_relevant=int(is_relevant)))

        query_vec = DbBasedSE1.translate(query)
        self.clf.train([query_vec], [is_relevant])
        self.save()

        # try:
        #     doc = self.es_collection.get(str(self.id))[1]['_source']
        # except:
        #     doc = self.make_index_entry()

        # # If relevant, extend the question_vector
        # if is_relevant:
        #     doc['question_vector'] = [t for t in set(doc['question_vector']).union(set(query_vec))]

        # # Either way, append the feedback
        # doc['faq']['feedback'] = doc['faq']['feedback'] + [(query_vec, is_relevant)]
        # # self.es_collection.put(str(self.id), doc)
        # # self.es_collection.index.refresh()

    def retrain(self):
        queries = []
        values = []
        for entry in self.feedback:
            queries.append(entry[0])
            values.append(int(entry[1]))
        clf = FilterClassifier()
        clf.train(queries, values)
        self._clf = clf
        self.save()

    def feedback_to_es(self):
        feedback = []
        for feedback_entry in self.feedback:
            feedback.append((DbBasedSE1.translate(feedback_entry['query']), int(feedback_entry['is_relevant'])))

    def make_index_entry(self):
        return dict(id=str(self.id),
                    question_vector=DbBasedSE1.translate(self.question),
                    answer_vector=DbBasedSE1.translate(self.answer),
                    feedback=self.feedback_to_es(),
                    channels=[str(self.channel.id)],
                    faq=self.to_dict())

    def put_to_es(self, refresh=True):
        """Put an encoded form of the document to elastic search"""
        doc = self.make_index_entry()
        self.es_collection.put(str(self.id), doc)
        self.is_active = True
        self.save()
        if refresh:
            self.es_collection.index.refresh()

    def to_dict(self, fields_to_show=None):
        full_dict = super(FAQ, self).to_dict()
        full_dict.pop('packed_clf')
        return full_dict

    def deploy(self, refresh=False):
        self.put_to_es(refresh)

    def withdraw(self, refresh=False):
        if self.is_active:
            self.is_active = False
            self.save()
            self.es_collection.delete(str(self.id))

            if refresh:
                self.es_collection.index.refresh()




