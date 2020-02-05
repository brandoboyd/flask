from solariat_bottle.api.base import ModelAPIView, api_request
from solariat_bottle.api.channels import ChannelAPIView
from solariat_bottle.api.smarttags import SmartTagAPIView
import solariat_bottle.api.exceptions as exc

from solariat.utils.timeslot import now
from solariat_bottle.commands.configure import ActivateChannel, DeleteChannel, SuspendChannel
from solariat_bottle.db.api_channel_command import ChannelAPICommand
from solariat_bottle.db.channel.base import Channel, SmartTagChannel

COMMANDS_MAPPING = {
    ChannelAPICommand.ACTIVATE: ActivateChannel,
    ChannelAPICommand.SUSPEND: SuspendChannel,
    ChannelAPICommand.DELETE: DeleteChannel
}


class ChannelCommandMixin():

    def _fetch_channel(self, **params):
        if 'channel_id' not in params:
            raise exc.ResourceDoesNotExist("The 'channel_id' parameter is required")
        channel_id = params['channel_id']

        try:
            self.channel = Channel.objects.get(channel_id)
        except Channel.DoesNotExist:
            raise exc.ResourceDoesNotExist("No channel with id='%s' exists in the system." % channel_id)

    def _execute_action(self, user):
        _command_class = COMMANDS_MAPPING[self.command]
        _command_class(channels=[self.channel]).update_state(user)
        ChannelAPICommand.objects.create(user=user,
                                         timestamp=now(),
                                         channel_id=str(self.channel.id),
                                         command=ChannelAPICommand.ACTIVATE)

        channel = Channel.objects.get(id=str(self.channel.id), include_safe_deletes=True)
        if isinstance(channel, SmartTagChannel):
            result = SmartTagAPIView._format_doc(channel)
        else:
            result = ChannelAPIView._format_doc(channel)
        return result

    @api_request
    def post(self, user, **kwargs):
        """ Perform the RPC command by the platform and command name"""
        self._fetch_channel(**kwargs)
        return dict(item=self._execute_action(user))


class ChannelActivateAPIView(ChannelCommandMixin, ModelAPIView):
    """
    Endpoint to administer the state of channels for a given account

    Parameters:
            :param token: <Required> - A valid user access token
            :param channel_id: <Required> - A existing channel id which we want to activate

        Output:
            Identical to the one returned by /api/v2.0/channels

        Sample request:
            curl http://staging.socialoptimizr.com/api/v2.0/activate_channel
    """
    model = ChannelAPICommand
    command = ChannelAPICommand.ACTIVATE
    endpoint = 'activate_channel'

    @classmethod
    def register(cls, app):
        view_func = cls.as_view(cls.endpoint)
        app.add_url_rule(cls.get_api_url(), view_func=view_func, methods=["POST", "GET", "PUT", "DELETE"])


class ChannelSuspendAPIView(ChannelCommandMixin, ModelAPIView):
    """
    Endpoint to administer the state of channels for a given account

    Parameters:
            :param token: <Required> - A valid user access token
            :param channel_id: <Required> - A existing channel id which we want to suspend

        Output:
            Identical to the one returned by /api/v2.0/channels

        Sample requests:
            curl http://staging.socialoptimizr.com/api/v2.0/suspend_channel
    """
    model = ChannelAPICommand
    command = ChannelAPICommand.SUSPEND
    endpoint = 'suspend_channel'

    @classmethod
    def register(cls, app):
        view_func = cls.as_view(cls.endpoint)
        app.add_url_rule(cls.get_api_url(), view_func=view_func, methods=["POST", "GET", "PUT", "DELETE"])


class ChannelDeleteAPIView(ChannelCommandMixin, ModelAPIView):
    """
    Endpoint to administer the state of channels for a given account

    Parameters:
            :param token: <Required> - A valid user access token
            :param channel_id: <Required> - A existing channel id which we want to delete

        Output:
            Identical to the one returned by /api/v2.0/channels

        Sample requests:
            curl http://staging.socialoptimizr.com/api/v2.0/delete_channel
    """
    model = ChannelAPICommand
    command = ChannelAPICommand.DELETE
    endpoint = 'delete_channel'

    @classmethod
    def register(cls, app):
        view_func = cls.as_view(cls.endpoint)
        app.add_url_rule(cls.get_api_url(), view_func=view_func, methods=["POST", "GET", "PUT", "DELETE"])

