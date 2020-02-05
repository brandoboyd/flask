from datetime import datetime
import solariat_bottle.api.exceptions as exc

from solariat_bottle.api.base import ModelAPIView, api_request
from solariat_bottle.db.classifiers import AuthTextClassifier


class ClassifiersAPIView(ModelAPIView):
    model = AuthTextClassifier
    endpoint = 'classifiers'
    commands = ['predict', 'train', 'retrain', 'reset']
    required_fields = ['name', 'type']

    @classmethod
    def register(cls, app):
        """ Queue API allows for extra commands, like 'fetch' and 'confirm' """
        url = cls.get_api_url()
        view_func = cls.as_view(cls.endpoint)
        app.add_url_rule(url, view_func=view_func, methods=['GET',])
        app.add_url_rule(url, view_func=view_func, methods=['POST',])
        app.add_url_rule(url, view_func=view_func, methods=['DELETE',])
        app.add_url_rule(cls.get_api_url('<_id>'),
                         view_func=view_func,
                         methods=['GET', 'PUT', 'DELETE'])

        url = cls.get_api_url('<command>')
        app.add_url_rule(url, view_func=view_func, methods=["POST",])

        url = cls.get_api_url('<command>/<classifier_id>')
        app.add_url_rule(url, view_func=view_func, methods=["POST",])

    @api_request
    def predict(self, user, *args, **kwargs):
        """
        Tied to the predict endpoint. Accepts POST requests and does a prediction returning scores for each sample

        Sample requests:
            Generic request by some filter:
                curl http://staging.socialoptimizr.com/api/v2.0/classifiers/predict

                POST Parameters:
                :param token: <Required> - A valid user access token
                :param classifiers: <Required>: [list] a list of classifier ids indicating which classifiers to apply
                :param samples: <Required> -  list of samples to classify. Each entry in the list is a dictionary.
                                              For text classification: {'text': <string>} The text to be classified.


        Output:
            A dictionary in the form
                {
                  "latency": 98,
                  "list": [
                    {
                      "score": 0.5,
                      "id": "5423f3b231eddd14ab477eea",
                      "name": "ClassifierOne",
                      "text": "This is some test post"
                    },
                    {
                      "score": 0.5,
                      "id": "5423f3b231eddd14ab477eea",
                      "name": "ClassifierOne",
                      "text": "This is some laptop post"
                    }
                  ],
                  "ok": true
                }
        """
        if 'classifiers' not in kwargs:
            error_msg = "Missing required parameter 'classifiers'."
            error_desc = "You are missing a required parameter 'classifiers'. This should be a list "
            error_desc += "of Classifier ids that will be used to compute prediction scores on the sample list."
            raise exc.InvalidParameterConfiguration(error_msg, description=error_desc)
        if 'samples' not in kwargs:
            error_msg = "Missing required parameter 'samples'"
            error_desc = "You are missing a required parameter 'samples'. This should be a list of "
            error_desc += "text samples to classify. Each entry should be a simple dictionary {'text': <content>}"
            raise exc.InvalidParameterConfiguration(error_msg, description=error_desc)
        result = []
        batch_start = datetime.utcnow()
        for classifier in AuthTextClassifier.objects(id__in=kwargs['classifiers']):
            score = classifier.batch_predict([sample['text'] for sample in kwargs['samples']])
            scores = [{'id': str(classifier.id),
                       'name': classifier.name,
                       'score': s['score'],
                       'text': s['text']} for s in score]
            result.extend(scores)
        latency = (datetime.utcnow() - batch_start).total_seconds()
        return {'list': result, 'latency': latency}

    def __train(self, samples):
        classifiers_cache = {}
        latencies = {}
        errors = []
        for sample_entry in samples:
            content = sample_entry['text']
            for classifer_id, value in sample_entry['values']:
                classifier_instance = classifiers_cache.get(classifer_id, False)
                if not classifier_instance:
                    try:
                        classifier_instance = AuthTextClassifier.objects.get(classifer_id)
                        classifiers_cache[classifer_id] = classifier_instance
                        latencies[classifer_id] = 0
                    except AuthTextClassifier.DoesNotExist:
                        errors.append("No classifier exists with id=%s. Skipping training for related samples." %
                                      classifer_id)
                batch_start = datetime.utcnow()
                classifier_instance.handle_accept(content) if value else classifier_instance.handle_reject(content)
                latencies[classifer_id] += (datetime.utcnow() - batch_start).total_seconds()
        return errors, latencies

    @api_request
    def train(self, user, *args, **kwargs):
        """
        Tied to the train endpoint. Accepts POST requests and does a training based on the input samples

        Sample requests:
            Generic request by some filter:
                curl http://staging.socialoptimizr.com/api/v2.0/classifiers/train

                POST Parameters:
                :param token: <Required> - A valid user access token
                :param samples: <Required> -  list of samples to classify. Each entry in the list is a dictionary:
                                              {'text': "This is a test post",
                                               'values': [(classifier1_id, 1), (classifier2_id, 1)],}

        Output:
            A dictionary in the form
            {
              "ok": true,
              "errors": [],
              "list": [
                {
                  "latency": 7,
                  "id": "5423fc8c31eddd17f7f96dc0"
                },
                {
                  "latency": 145,
                  "id": "5423fc8c31eddd17f7f96dbf"
                }
              ],
              "skipped_samples": 0
            }

        In case of missing parameter:
            {
              "code": 113,
              "ok": false,
              "error": "Missing required parameter 'samples'",
              "description": "You are missing a required parameter 'samples'.
                              This should be a list of text samples to classify.
                              Each entry should be a simple dictionary
                              {'text': <content>, values: [(classifier1_id, value), (classifier2_id, value), ..]}"
            }
        """
        if 'samples' not in kwargs:
            error_msg = "Missing required parameter 'samples'"
            error_desc = "You are missing a required parameter 'samples'. This should be a list of "
            error_desc += "text samples to classify. Each entry should be a simple dictionary "
            error_desc += "{'text': <content>, values: [(classifier1_id, value), (classifier2_id, value), ..]}"
            raise exc.InvalidParameterConfiguration(error_msg, description=error_desc)
        errors, latencies = self.__train(kwargs['samples'])
        result = []
        for entry in latencies:
            result.append({'id': entry,
                           'latency': latencies[entry]})
        result = dict(ok=len(errors) == 0,
                      list=result)
        result['skipped_samples'] = len(errors)
        result['errors'] = list(set(errors))
        return result

    @api_request
    def retrain(self, user, *args, **kwargs):
        """
         Tied to the retrain endpoint. Accepts POST requests and does a retraining of the input classifier ids

         Sample requests:
            Generic request by some filter:
                curl http://staging.socialoptimizr.com/api/v2.0/classifiers/retrain

                POST Parameters:
                :param token: <Required> - A valid user access token
                :param classifiers: <Required>: [list] a list of classifier ids indicating which classifiers to apply

         Output:
            A dictionary in the form
            {
              "ok": true,
              "errors": [],
              "list": [
                {
                  "latency": 2,
                  "id": "5424036831eddd1a7624a252"
                },
                {
                  "latency": 2,
                  "id": "5424036731eddd1a7624a251"
                }
              ],
              "skipped_samples": 0
            }

        """
        if 'classifiers' not in kwargs:
            error_msg = "Missing required parameter 'classifiers'."
            error_desc = "You are missing a required parameter 'classifiers'. This should be a list "
            error_desc += "of Classifier ids that will be used to compute prediction scores on the sample list."
            raise exc.InvalidParameterConfiguration(error_msg, description=error_desc)
        latencies = {}
        errors = []
        for classifier in AuthTextClassifier.objects(id__in=kwargs['classifiers']):
            batch_start = datetime.utcnow()
            classifier.retrain()
            latencies[str(classifier.id)] = (datetime.utcnow() - batch_start).total_seconds()
        train_latencies = {}
        errors = []
        if 'sample' in kwargs:
            errors, train_latencies = self.__train(kwargs['samples'])
        result = []
        for entry in latencies:
            if entry in train_latencies:
                latencies[entry] += train_latencies[entry]
            result.append({'id': entry,
                           'latency': latencies[entry]})
        result = dict(ok=len(errors) == 0,
                      list=result)
        result['skipped_samples'] = len(errors)
        result['errors'] = list(set(errors))
        return result

    @api_request
    def reset(self, user, instance, *args, **kwargs):
        instance.reset()
        instance.reload()
        return self._format_single_doc(instance)

    @api_request
    def _post(self, user, _id=None, *args, **kwargs):
        """ The standard POST request. Create a new instance and returns the value in the same
         form as a GET request would. """
        for entry in self.required_fields:
            if entry not in kwargs:
                raise exc.InvalidParameterConfiguration("Expected required field: '{}'".format(entry))
        return self._format_single_doc(AuthTextClassifier.objects.create_by_user(user, *args, **kwargs))

    def post(self, command=None, classifier_id=None, *args, **kwargs):
        if command in self.commands:
            if command == 'predict':
                return self.predict(*args, **kwargs)
            if command == 'train':
                return self.train(*args, **kwargs)
            if command == 'retrain':
                return self.retrain(*args, **kwargs)
            if command == 'reset':
                try:
                    instance = AuthTextClassifier.objects.get(classifier_id)
                except AuthTextClassifier.DoesNotExist:
                    raise exc.ResourceDoesNotExist("No classifier with id=%s found in the system." % classifier_id)
                return self.reset(instance, *args, **kwargs)
        return self._post(*args, **kwargs)

    def get(self, *args, **kwargs):
        """
        A GET request on a classifier objects. This routes generic requests by a filter and specific requests by
        ID. Sample objects returned are:

        Sample requests:
            Generic request by some filter:
                curl http://staging.socialoptimizr.com/api/v2.0/classifiers

                GET Parameters:
                :param token: <Required> - A valid user access token
                :param name: <Optional> - Only Classifiers with this name are returned
                :param type: <Optional> - Only Classifiers with this type are returned

            Specific request by id:
                curl http://staging.socialoptimizr.com/api/v2.0/classifiers/5423e7c831eddd1107b7092e

                GET Parameters:
                :param token: <Required> - A valid user access token

        Output:
            A dictionary in the fork {'ok': true, 'item': <classifier json>} for specific requests or
            {'ok': true, 'list': [<classifier json>, ....] in case of generic requests

        In both cases, <classifier json> will have the following fields:
            {
              "negative_samples": 0,
              "name": "ClassifierTwo",
              "id": "5423e7c831eddd1107b7092e",
              "metadata": {
                "keywords": [
                  "Test",
                  "Testing"
                ],
                "skip_keywords": [
                  "Skip"
                ],
                "watchwords": [
                  "Tester"
                ]
              },
              "type": "keyword_augmented",
              "uri": "http://127.0.0.1:3031/api/v2.0/classifiers/5423e7c831eddd1107b7092e",
              "positive_samples": 0
            }
        """
        return self._get(*args, **kwargs)

    def delete(self, *args, **kwargs):
        return self._delete(*args, **kwargs)

    @classmethod
    def _format_doc(cls, item):
        """ Format a post ready to be JSONified """
        return dict(name=item.name,
                    type=item.type,
                    id=str(item.id),
                    uri=cls._resource_uri(item),
                    positive_samples=item.accept_count,
                    negative_samples=item.reject_count,
                    metadata=item.metadata)
