from solariat.db.abstract import SonDocument, Document, Manager
from solariat.db import fields
from solariat.exc.base import AppException


class TaskData(SonDocument):
    updated_at = fields.DateTimeField()
    total = fields.NumField()
    done = fields.NumField()

    @property
    def status(self):
        return 'training' if 0 < self.done < self.total else 'idle'

    @property
    def progress(self):
        return int(100 * (self.done or 0.0) / (self.total or 1.0))

    def to_dict(self, fields_to_show=None):
        task = self
        json_data = super(TaskData, self).to_dict(fields_to_show)
        json_data.update(
            progress=self.progress,
            status=task.status,
            updated_at=task.updated_at and str(task.updated_at)
        )
        return json_data


class PredictorModelData(SonDocument):
    """Embedded model information to be used in Predictor
    """
    model_id = fields.ObjectIdField()  # reference to PredictorModel

    # denormalized from PredictorModel
    display_name = fields.StringField()
    weight = fields.NumField()
    task_data = fields.EmbeddedDocumentField(TaskData)

    @staticmethod
    def _get_model_data(model):
        return dict(model_id=model.id,
                    display_name=model.display_name,
                    weight=model.weight,
                    task_data=model.task_data)

    @classmethod
    def init_with_model(cls, model):
        return cls(**cls._get_model_data(model))

    def sync_with_model_instance(self, model):
        self.__dict__.update(self._get_model_data(model))

    def __eq__(self, other):
        return isinstance(other, self.__class__) and other.model_id == self.model_id

    def __hash__(self):
        return hash(str(self.model_id))


class PredictorModelManager(Manager):

    def create(self, *args, **kw):
        if 'train_data_percentage' in kw:
            if kw['train_data_percentage'] > 100 or kw['train_data_percentage'] < 0:
                raise AppException("'train_data_percentage' needs to be between 0 and 100")
        return super(PredictorModelManager, self).create(*args, **kw)


class PredictorModel(Document):
    collection = 'PredictorModel'
    allow_inheritance = True

    version = fields.NumField()
    predictor = fields.ReferenceField('BasePredictor')
    parent = fields.ObjectIdField()
    weight = fields.NumField()
    display_name = fields.StringField()
    description = fields.StringField()
    # is_active = fields.BooleanField(default=False)
    task_data = fields.EmbeddedDocumentField(TaskData)
    last_run = fields.DateTimeField()
    context_features = fields.ListField(fields.DictField())
    action_features = fields.ListField(fields.DictField())
    train_data_percentage = fields.NumField(default=80)
    n_rows = fields.NumField()
    min_samples_thresould = fields.NumField(default=1)

    from_dt = fields.DateTimeField()
    to_dt = fields.DateTimeField()

    def score(self, *args, **kwargs):
        pass

    def feedback(self, *args, **kwargs):
        pass

    def search(self, *args, **kwargs):
        pass

    def to_json(self, *args, **kwargs):
        from solariat_bottle.db.predictors.base_predictor import PredictorConfigurationConversion
        data = super(PredictorModel, self).to_json(*args, **kwargs)
        data = PredictorConfigurationConversion.python_to_json(data)
        return data
