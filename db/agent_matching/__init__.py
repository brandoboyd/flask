

def clear_data(account_id):
    from solariat_bottle.db.account import Account
    from solariat_bottle.db.predictors.factory import delete_agent_matching_predictor, create_agent_matching_predictor
    account = Account.objects.get(account_id)
    CustomerProfile = account.get_customer_profile_class()
    AgentProfile = account.get_agent_profile_class()
    delete_agent_matching_predictor(account_id)
    create_agent_matching_predictor(account_id)


def create_customer(first_name, last_name, age, account_id, location, sex, account_balance,
                    last_call_intent, num_calls, seniority):
    from solariat_bottle.db.account import Account
    account = Account.objects.get(account_id)
    CustomerProfile = account.get_customer_profile_class()
    return CustomerProfile.objects.get_or_create(first_name=first_name,
                                          last_name=last_name,
                                          age=age,
                                          account_id=account_id,
                                          location=location,
                                          assigned_labels=[],
                                          sex=sex,
                                          account_balance=account_balance,
                                          last_call_intent=last_call_intent,
                                          num_calls=num_calls,
                                          seniority=seniority)


def create_agent(first_name, last_name, age, location, sex, account_id, skillset, occupancy,
                 products, english_fluency, seniority):
    from solariat_bottle.db.account import Account
    account = Account.objects.get(account_id)
    AgentProfile = account.get_agent_profile_class()
    return AgentProfile.objects.get_or_create(first_name=first_name,
                                       last_name=last_name,
                                       age=age,
                                       location=location,
                                       sex=sex,
                                       account_id=account_id,
                                       skillset=skillset,
                                       occupancy=occupancy,
                                       products=products,
                                       english_fluency=english_fluency,
                                       seniority=seniority)

