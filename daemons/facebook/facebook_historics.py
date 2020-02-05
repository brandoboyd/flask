from solariat_bottle.db.user import User
from solariat_bottle.daemons.base import BaseHistoricSubscriber
from solariat_bottle.db.historic_data import SUBSCRIPTION_CREATED, FacebookHistoricalSubscription, \
    SUBSCRIPTION_RUNNING, SUBSCRIPTION_FINISHED, SUBSCRIPTION_ERROR
from solariat_bottle.settings import LOGGER, FB_DATA_PULL_USER
from solariat_bottle.tasks.facebook import fb_get_history_pm, fb_get_history_data_for


class FacebookSubscriber(BaseHistoricSubscriber):

    def __init__(self, subscription, user=None):

        self.subscription = subscription
        self.channel = self.subscription.channel
        self.user = user

    def get_status(self):
        return self.subscription.status

    def start_historic_load(self):
        running_subscriptions = FacebookHistoricalSubscription.objects.find(status=SUBSCRIPTION_RUNNING,
                                                                            channel_id=str(self.channel.id))
        if len(running_subscriptions) > 0:
            LOGGER.warning("Only single running subscription available for a channel at single moment")
            return False

        if self.subscription.status == SUBSCRIPTION_CREATED:
            LOGGER.info("Starting new facebook subscription.")
            self._load_history()
            LOGGER.info("Historic load finished successfully.")
        else:
            LOGGER.warning("This current subscription already has status: %s. Cannot start again." %
                           self.subscription.status)
            return False

    def _load_history(self):

        self.subscription.status = SUBSCRIPTION_RUNNING
        self.subscription.save()

        default_user = self.user if self.user is not None else User.objects.get(email=FB_DATA_PULL_USER)

        targets = self.subscription.get_history_targets()
        self.subscription.actionable = targets
        self.subscription.save()

        try:
            for target in targets:
                fb_get_history_data_for.sync(self.channel, target, default_user, self.subscription.from_date,
                                             self.subscription.to_date)
                if target in self.channel.facebook_page_ids:
                    fb_get_history_pm.sync(self.channel, target, default_user, self.subscription.from_date,
                                      self.subscription.to_date)

                self.subscription.actionable.remove(target)
                self.subscription.finished.append(target)
                self.subscription.save()

            self.subscription.status = SUBSCRIPTION_FINISHED
            self.subscription.save()

        except Exception, e:
            self.subscription.status = SUBSCRIPTION_ERROR
            self.subscription.save()
            raise e

