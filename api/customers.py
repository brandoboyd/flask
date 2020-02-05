from .base import BaseAPIView, api_request


class CustomersAPIView(BaseAPIView):

    endpoint = 'customers'

    @api_request
    def get(self, user, **kwargs):
        phone = kwargs.get('phone')
        c_id = kwargs.get('id')

        ignored_fields = ['account_id',
                          'actor_num',
                          'groups',
                          'linked_profile_ids']

        CustomerProfile = user.account.get_customer_profile_class()

        customer = None
        if c_id:
            try:
                customer = CustomerProfile.objects.get(id=c_id)
            except CustomerProfile.DoesNotExist:
                customer = None

        if phone is not None and customer is None:
            try:
                customer = CustomerProfile.objects.get(phone=str(phone))
            except CustomerProfile.DoesNotExist:
                customer = None
        if customer:
            item = customer.to_dict()
            for key in ignored_fields:
                if key in item:
                    item.pop(key)
            return {'item': item, 'ok': True}
        account_id = kwargs.get('account_id') or user.account.id
        if account_id and not (phone or c_id):
            customers = CustomerProfile.objects()[:]
            c_list = []
            for cust in customers:
                item = cust.to_dict()
                for key in ignored_fields:
                    if key in item:
                        item.pop(key)
                c_list.append(item)
            return {'ok': True, 'list': c_list}

        return {'ok': False, 'error': "No customer found with info " + str(kwargs)}

