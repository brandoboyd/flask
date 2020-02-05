#from solariat_bottle.settings               import LOGGER
from solariat_bottle.api.base import ModelAPIView, ReadOnlyMixin, api_request
from solariat_bottle.api.smarttags import SmartTagAPIView
from solariat_bottle.db.channel.base import ServiceChannel, Channel
from solariat_bottle.db.channel.faq import FAQChannel
from solariat_bottle.db.channel.web_click import WebClickChannel
from solariat_bottle.db.dynamic_classes import InfomartChannel, RevenueChannel, NPSChannel
from solariat_bottle.db.channel.chat import ChatServiceChannel
from solariat_bottle.db.channel.twitter import TwitterServiceChannel
from solariat_bottle.db.channel.facebook import FacebookServiceChannel


class ChannelAPIView(ReadOnlyMixin, ModelAPIView):
    model = ServiceChannel
    endpoint = 'channels'

    platforms = {
        'chat': ChatServiceChannel,
        'web': WebClickChannel,
        'faq': FAQChannel,
        'imart': InfomartChannel,
        'revenue': RevenueChannel,
        'nps': NPSChannel
    }

    @classmethod
    def register(cls, app):
        """ Queue API allows for extra commands, like 'fetch' and 'confirm' """
        url = cls.get_api_url()
        view_func = cls.as_view(cls.endpoint)
        app.add_url_rule(url, view_func=view_func, methods=['GET',])
        app.add_url_rule(cls.get_api_url('<_id>'),
                         view_func=view_func,
                         methods=['GET',])

    def get(self, _id=None, *args, **kwargs):
        """
        Handler for a specific get request On the ServiceChannel collection. Supports two types
        of requests, generic requests on the collection and specific item requests based on ids.

        Generic request example:
        ------------------------
            Sample request:
                curl http://staging.socialoptimizr.com/api/v2.0/channels?token={{your-token}}

            Parameters:
                :param token: <Required> - A valid user access token

            Output:
                A dictionary in the form {'ok': true, 'list': [list of actual channel JSON's]}
                In case of no matched channels, list will be empty

            Sample response:
                HTTP-200
                {
                  "ok": true,
                  "list": [
                    {
                      "status": "Interim",
                      "skipwords": [],
                      "description": null,
                      "title": "TSC",
                      "uri": "http://127.0.0.1:3031/api/v2.0/channels/54118aa931eddd173ce02ca1",
                      "watchwords": [],
                      "keywords": [],
                      "tracked_usernames": [],
                      "id": "54118aa931eddd173ce02ca1",
                      "platform": "Twitter",
                      "smart_tags": [
                                      {
                                        "status": "Active",
                                        "skipwords": [],
                                        "usernames": [],
                                        "description": null,
                                        "title": "tag",
                                        "influence_score": 0,
                                        "uri": "http://127.0.0.1:3031/api/v2.0/smarttags/5411995c31eddd1d32920c4d",
                                        "watchwords": [],
                                        "intentions": [],
                                        "keywords": [],
                                        "id": "5411995c31eddd1d32920c4d"
                                      }
                                    ],
                    },
                    {
                    "status": "Active",
                    "description": null,
                    "title": "TSC",
                    "uri": "http://127.0.0.1:3031/api/v2.0/channels/54118aa931eddd173ce02cba",
                    "tracked_groups": [],
                    "tracked_events": [],
                    "id": "54118aa931eddd173ce02cba",
                    "tracked_pages": [],
                    "platform": "Twitter",
                    "smart_tags": []
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
                A dictionary in the form {'ok': true, 'list': [list of actual channel JSON's]}
                In case of no matched channels, return a 404

            Sample responses:

                Valid Native Channel:
                    HTTP-200
                    {
                      "item": {
                        "status": "Interim",
                        "description": null,
                        "title": "TSC",
                        "id": "54118aa931eddd173ce02cef",
                        "uri": "http://127.0.0.1:3031/api/v2.0/channels/54118aa931eddd173ce02cef",
                        "smart_tags": []
                      },
                      "ok": true
                    }

                Valid Twitter Service Channel:
                    HTTP-200
                    {
                      "item": {
                        "status": "Interim",
                        "skipwords": [],
                        "description": null,
                        "title": "TSC",
                        "uri": "http://127.0.0.1:3031/api/v2.0/channels/54118aa931eddd173ce02cff",
                        "watchwords": [],
                        "keywords": [],
                        "tracked_usernames": [],
                        "id": "54118aa931eddd173ce02cff",
                        "smart_tags": []
                      },
                      "ok": true
                    }

                Valid Facebook Service Channel:
                    HTTP-200
                    {
                      "item": {
                        "status": "Active",
                        "description": null,
                        "title": "TSC",
                        "uri": "http://127.0.0.1:3031/api/v2.0/channels/54118aa931eddd173ce02cba",
                        "tracked_groups": [],
                        "tracked_events": [],
                        "id": "54118aa931eddd173ce02cba",
                        "tracked_pages": [],
                        "smart_tags": [
                                      {
                                        "status": "Active",
                                        "skipwords": [],
                                        "usernames": [],
                                        "description": null,
                                        "title": "tag",
                                        "influence_score": 0,
                                        "uri": "http://127.0.0.1:3031/api/v2.0/smarttags/5411995c31eddd1d32920c4d",
                                        "watchwords": [],
                                        "intentions": [],
                                        "keywords": [],
                                        "id": "5411995c31eddd1d32920c4d"
                                      }
                                    ],
                      },
                      "ok": true
                    }

                Invalid Document Id:
                    HTTP-404
                    {
                      "code": 34,
                      "error": "There is no channel with id={{invalid_id}} in the system."
                    }

        """
        return super(ChannelAPIView, self).get(_id=_id, *args, **kwargs)

    @api_request
    def _get(self, user, _id=None, *args, **kwargs):
        """ A sensical generic repsonse to a Model GET request. """
        if _id:
            if _id in self.platforms.keys():
                model = self.platforms[_id]
                docs = model.objects.find_by_user(user)
                docs = self._format_multiple_docs(docs)
                return docs
            return self._get_doc_by_id(user, _id, *args, **kwargs)
        else:
            return self._fetch_docs(user, *args, **kwargs)

    @classmethod
    def _format_doc(cls, item):
        if isinstance(item, TwitterServiceChannel):
            return dict(id=str(item.id),
                        uri=cls._resource_uri(item),
                        title=item.title,
                        status=item.status,
                        description=item.description,
                        tracked_usernames=item.twitter_usernames,
                        keywords=item.keywords,
                        skipwords=item.skipwords,
                        watchwords=item.inbound_channel.watchwords,
                        platform='Twitter',
                        smart_tags=[SmartTagAPIView()._format_doc(tag) for tag in item.inbound_channel.smart_tags])
        elif isinstance(item, FacebookServiceChannel):
            return dict(id=str(item.id),
                        uri=cls._resource_uri(item),
                        title=item.title,
                        status=item.status,
                        description=item.description,
                        tracked_pages=item.facebook_pages,
                        tracked_groups=item.tracked_fb_groups,
                        tracked_events=item.tracked_fb_events,
                        platform='Facebook',
                        smart_tags=[SmartTagAPIView()._format_doc(tag) for tag in item.inbound_channel.smart_tags])
        elif isinstance(item, ServiceChannel):
            return dict(id=str(item.id),
                        uri=cls._resource_uri(item),
                        title=item.title,
                        status=item.status,
                        description=item.description,
                        platform=item.platform,
                        smart_tags=[SmartTagAPIView()._format_doc(tag) for tag in item.inbound_channel.smart_tags])
        else:
            return dict(id=str(item.id),
                        title=item.title,
                        status=item.status,
                        description=item.description,
                        platform=item.platform)
