import solariat_bottle.api.exceptions as exc
from solariat_bottle.api.base import ModelAPIView, ReadOnlyMixin, api_request
from solariat_bottle.db.channel.base import SmartTagChannel, Channel


class SmartTagAPIView(ReadOnlyMixin, ModelAPIView):
    model = SmartTagChannel
    endpoint = 'smarttags'

    @api_request
    def get(self, user, _id=None, *args, **kwargs):
        """
        Handler for a specific get request On the SmartTag collection. Supports two types
        of requests, generic requests on the collection and specific item requests based on ids.

        Generic request example:
        ------------------------

            Sample request:
                curl http://staging.socialoptimizr.com/api/v2.0/smarttags?token={{your-token}}

            Parameters:
                :param token: <Required> - A valid user access token
                :param channel: <Optional> - If present should be the id of a channel from the system for which
                                             we want spart tags returned.

            Output:
                A dictionary in the form {'ok': true, 'list': [list of actual channel JSON's]}
                In case of no matched channels, list will be empty

            Sample response:
                HTTP-200
                {
                  "ok": true,
                  "list": [
                    {
                      "status": "Active",
                      "skipwords": [],
                      "usernames": [],
                      "description": null,
                      "title": "tag",
                      "influence_score": 0,
                      "uri": "http://127.0.0.1:3031/api/v2.0/smarttags/54119c5d31eddd1e7089dc40",
                      "watchwords": [],
                      "intentions": [],
                      "keywords": [],
                      "id": "54119c5d31eddd1e7089dc40"
                    }
                  ]
                }

        Specific request example:
        -------------------------

            Sample request:
                curl http://staging.socialoptimizr.com/api/v2.0/channels?token={{your-token}}&id={{channel-id}}

            Parameters:
                :param token: <Required> - A valid user access token
                :param doc_id: <Required> - A document ID for a service channel

            Output:
                A dictionary in the fork {'ok': true, 'list': [list of actual channel JSON's]}
                In case of no matched channels, return a 404

            Sample responses:

                Valid Native Channel:
                    HTTP-200
                    {
                      "item": {
                        "status": "Active",
                        "skipwords": [],
                        "usernames": [],
                        "description": null,
                        "title": "tag",
                        "influence_score": 0,
                        "uri": "http://127.0.0.1:3031/api/v2.0/smarttags/54119c5d31eddd1e7089dc40",
                        "watchwords": [],
                        "intentions": [],
                        "keywords": [],
                        "id": "54119c5d31eddd1e7089dc40"
                      },
                      "ok": true
                    }


                Invalid Document Id:
                    HTTP-404
                    {
                      "code": 34,
                      "error": "There is no smart tag with id=invalid_id in the system."
                    }
        """
        if _id:
            # Specific GET by an id
            try:
                smart_tag = SmartTagChannel.objects.get_by_user(user, id=_id)
            except SmartTagChannel.DoesNotExist:
                raise exc.ResourceDoesNotExist("No smart tag with id=%s found in the system." % _id)
            return dict(ok=True, item=self._format_doc(smart_tag))
        else:
            # General fetch
            if 'channel' in kwargs:
                # We need a specific fetch based on channel
                try:
                    channel = Channel.objects.get_by_user(user, id=kwargs['channel'])
                except Channel.DoesNotExist:
                    raise exc.ResourceDoesNotExist("No channel with id=%s found in the system." % kwargs['channel'])
                smart_tag_list = channel.smart_tags
                return dict(ok=True, list=[self._format_doc(st) for st in smart_tag_list])
            else:
                # Just default so the general fetch
                smart_tag_list = SmartTagChannel.objects.find_by_user(user, **kwargs)
            return dict(ok=True, list=[self._format_doc(st) for st in smart_tag_list])

    @classmethod
    def _format_doc(cls, item):
        return dict(id=str(item.id),
                    uri=cls._resource_uri(item),
                    title=item.title,
                    status=item.status,
                    description=item.description,
                    keywords=item.keywords,
                    usernames=item.usernames,
                    watchwords=item.watchwords,
                    influence=int(round(item.influence_score * 100)),
                    skipwords=item.skip_keywords,
                    intentions=item.intention_types)
