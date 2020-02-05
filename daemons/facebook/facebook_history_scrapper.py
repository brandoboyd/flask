import requests

from solariat_bottle.utils.facebook_driver import FacebookDriver


class FacebookHistoryScrapper(object):

    def __init__(self, channel, user=None, driver = None, token=None):

        self.channel = channel
        self.user = user
        self.token = token if token is not None else self.channel.get_access_token(user)
        self.driver = driver if driver is not None else FacebookDriver(self.token)

    def get_comments(self, target, since=None, until=None, limit=None):
        target += '/comments'
        return self.__request(since, until, limit, target)

    def get_posts(self, target, since=None, until=None, limit=None):
        target += '/feed'
        return self.__request(since, until, limit, target)

    def get_events(self, target, since=None, until=None, limit=None):
        target += '/events'
        return self.__request(since, until, limit, target)

    def get_groups(self, target, since=None, until=None, limit=None):
        target += '/groups'
        return self.__request(since, until, limit, target)

    def get_paged_data(self, url):
        return requests.get(url)

    def get_page_private_messages(self, target, since=None, until=None, limit=None):
        token = self.driver.obtain_new_page_token(target)
        driver = FacebookDriver(token)
        target += '/conversations'
        return self.__request(since, until, limit, target, driver)

    def handle_data_item(self, data, handler, target_id):
        parsed = handler.prepare(data, target_id, self.channel, self.driver)
        return parsed

    def __request(self, since, until, limit, target='me', driver=None):
        from solariat_bottle.settings import LOGGER
        params = {}
        if since:
            params['since'] = since
        if until:
            params['until'] = until
        if limit:
            params['limit'] = limit

        driver = driver if driver is not None else self.driver
        try:
            return driver.request(target, params)
        except Exception, ex:
            LOGGER.error("Facebook request from channel: %s to target: %s failed with error %s" % (
                (self.channel.id, self.channel.title), target, str(ex)))
            raise
