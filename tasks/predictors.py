import numpy as np
from solariat_bottle.settings import LOGGER
from solariat_bottle.jobs.manager import job, manager, terminate_handler


MAX_DATA_SIZE = 2 ** 30     # Avoid any memory issues that we might run into from vectorization


def retrain_function(predictor, models):
    from copy import deepcopy

    for model in models:
        backup_model_data = deepcopy(model.data)
        predictor.select_model(model)
        predictor.features_space_size(model)
        try:
            manager.produce_state_update({'model': model.display_name,
                                          'progress': model.task_data.progress})
            predictor.train_models(model=model)
            manager.produce_state_update({'model': model.display_name,
                                          'progress': model.task_data.progress})

            predictor.save_model(model)
        except Exception, ex:
            # TODO: This needs some user notification somehow!
            LOGGER.exception(ex)
            model.data = backup_model_data
            model.save()

@job('model_training')
def retrain_classifier(predictor, models):
    retrain_function(predictor, models)

@terminate_handler(retrain_classifier)
def stop_models_training(predictor, models):
    for model in models:
        model.task_data = None
        model.save()
