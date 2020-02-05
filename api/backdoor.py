from solariat_bottle.api.base import BaseAPIView, api_request, _get_request_data
from solariat_bottle.db.account import Account


def clean_agents(*args, **kwargs):
    account_id = kwargs.get('gsa-account-id')
    account = Account.objects.get(account_id)
    AgentProfile = account.get_agent_profile_class()
    deleted = AgentProfile.objects.remove(account_id=account_id)
    return dict(ok=True, deleted=deleted)


# Mapping between task names and actual task on our side
TASK_MAPPING = {
    'clean_agents': clean_agents,
}


class BackdoorAPIView(BaseAPIView):
    endpoint = 'backdoor/<command>'

    @api_request
    def dispatch_request(self, user, command=None, **kwargs):
        """ Perform the RPC command by the platform and command name"""
        if not user.is_superuser:
            return dict(ok=False, error="Only superusers have backdoor access.")

        data = _get_request_data()
        backdoor_task = TASK_MAPPING[command]
        return backdoor_task(**data)

    @classmethod
    def register(cls, app):
        view_func = cls.as_view(cls.__name__)
        app.add_url_rule(cls.get_api_url(), view_func=view_func, methods=["GET", "POST"])
