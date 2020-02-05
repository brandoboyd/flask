from solariat_bottle.db.predictors.abc_predictor import BaseFeatureExtractor


class CustomerFeatureExtractor(BaseFeatureExtractor):

    def __compute_balance_segment(self, customer_profile):
        computed_segment = 'HOMELESS'
        for (min_balance, segment) in [(1000, 'POOR'), (10000, 'AVERAGE'), (100000, 'WEALTHY'), (500000, 'HIGHROLLER')]:
            if min_balance < customer_profile.account_balance:
                computed_segment = segment
                continue
            else:
                break
        return computed_segment

    def __compute_age_segment(self, customer_profile):
        computed_segment = 'UNBORN'
        for (max_age, segment) in [(30, 'YOUNG'), (50, 'MIDAGE'), (100000, 'OLD')]:
            if max_age > customer_profile.age:
                return segment
            else:
                break
        return computed_segment

    def construct_feature_space(self, customer_profile, features_metadata=None):
        if features_metadata:
            pass # For now we can't use this since we don't know what makes sense to use as 'helper' for features

        return {"content": [self.__compute_balance_segment(customer_profile)] +
                           [self.__compute_age_segment(customer_profile)] +
                           [customer_profile.sex]}

