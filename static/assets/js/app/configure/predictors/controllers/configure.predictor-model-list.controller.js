(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('PredictorModelListController', PredictorModelListController);

  /** @ngInject */
  function PredictorModelListController($location,
                                        $timeout,
                                        $routeParams,
                                        $scope,
                                        PredictorsRest,
                                        SystemAlert) {
    var Predictors = new PredictorsRest();
    $scope.selectedModels = [];
    $scope.trainedModels = [];

    $scope.selectRow = function (selected) {
      var found = _.find($scope.selectedModels, {id: selected.id});

      if (found) {
        _.remove($scope.selectedModels, selected)
      } else {
        $scope.selectedModels.push(selected)
      }
    };

    $scope.getRetrainLabel = function (selectedModel) {
      var state = selectedModel ? selectedModel.state : null;
      var status = selectedModel ? selectedModel.status : null;
      if (state == 'NEW' && status == 'INACTIVE') {
        return "Train"
      } else if (state == 'TRAINED' && status == 'INACTIVE') {
        return "Retrain"
      } else if (state == 'LOCKED' && status == 'ACTIVE') {
        return "Copy"
      } else {
        return ""
      }
    };

    $scope.onChangeModelMix = function (model) {
      if (!model) {
        return;
      }
      model.weight_error = (model.weight < 0 || model.weight > 100000);
      if (!model.weight_error) {
        Predictors.updateModel(model.predictor, model.id, {'weight': model.weight});
      }
    };

    var predictorId = $routeParams.predictorId,
        viewModelBase = {
          filters: {
            display_name: '',
            state: '',
            status: '',
            predicate: function (item) {
              var f = viewModelBase.filters,
                match = true;
              if (f.display_name.trim()) {
                match = match && (
                  item.display_name +
                  item.id +
                  item.status +
                  item.state).toLowerCase().indexOf(f.display_name.trim().toLowerCase()) > -1;
              }
              _(['status', 'state']).each(function (attr) {
                if (f[attr]) {
                  match = match && item[attr] == f[attr];
                }
              });
              return match;
            }
          },
          table: {
            sort: {
              predicate: 'display_name',
              reverse: false
            }
          },

          "create": function () {
            $location.path('/predictors/' + predictorId + '/models/edit/');
          },
          "delete": function () {
            _.each($scope.selectedModels, function (item) {
              if (item.task_data !== null & item.task_data.progress < 100) {
                SystemAlert.error('Model "' + item.display_name + '" cannot be deleted because training is not done',
                    3000);
              } else {
                Predictors.removeModel(predictorId, item.id).success(function (res) {
                    loadModels();
                    SystemAlert.info('Model "' + item.display_name + '" removed from database', 3000);
                });
              }
            });
          },
          shouldActivate: function () {
            // enable when some selected are INACTIVE
            // TODO: this is dirty way to remove tooltip accessing DOM on every false boolean...
            // bind watcher as ng-disabled with such as iteration and return boolean - is not good idea
            var isEnabled = _.some($scope.selectedModels, function (model) {
              return model.status == 'INACTIVE' && model.state !== 'NEW'
            });

            if(!isEnabled) {
              angular.element('.tooltip').remove();
            }

            return isEnabled;
          },
          shouldDeactivate: function () {
            // status: NEW or TRAINED also might exist which is possible to deactivate
            // disable when all selected are INACTIVE
            var isDisabled = !_.all($scope.selectedModels, {status: 'INACTIVE'});

            if (!isDisabled) {
              angular.element('.tooltip').remove();
            }

            return isDisabled;
          },
          activate: function () {
            _.each($scope.selectedModels, function (item) {
              Predictors.doModelAction(predictorId, item.id, 'activate').success(function () {
                loadModels();
                SystemAlert.success("Model activated.", 3000);
              });
            });
          },
          deactivate: function (item) {
            _.each($scope.selectedModels, function (item) {
              Predictors.doModelAction(predictorId, item.id, 'deactivate').success(function () {
                loadModels();
                SystemAlert.success("Model deactivated.", 3000);
              });
            });
          },
          redirectAll: function () {
            $location.path('/predictors/' + predictorId + '/models/')
          },
          "editPath": function (item) {
            return '#/predictors/' + predictorId + '/models/edit/' + item.id;
          },
          "predictorEditPath": function () {
            return '#/predictors/' + predictorId;
          },
          resetClassifier: function (item) {
            Predictors.doModelAction(predictorId, item.id, 'reset').success(function () {
              loadModels();
              SystemAlert.success("Model " + item.display_name + " has been reset.", 5000);
            });
          },
          retrainClassifier: function (item) {
            var message = "Retrain task submitted for a model.";
            var task = 'retrain';
            if ($scope.getRetrainLabel(item) == "Copy") {
              message = "Copying a model...";
              task = 'copy'
            } else {
              message = "Retraining a model...";
              task = 'retrain'
            }
            item.predictorId = predictorId;
            var model = item;
            Predictors.doModelAction(predictorId, item.id, task).success(function (resp) {
              var updatedModels = resp.data.list;

              // refresh if new models returned
              for (var modelIdx in updatedModels) {
                if (_.pluck($scope.items, 'id').indexOf(updatedModels[modelIdx].id) < 0) {
                  loadModels();
                  break;
                }
              }

              console.log("Watching updated models " + updatedModels);
              watchModels(updatedModels);
              SystemAlert.success(message + ' ' + item.display_name, 5000);
            });
          },
          upsertFeedback: function (item) {
            var message = "Upsert feedback task submitted for a model.";
            if ($scope.getRetrainLabel(item) == "Copy") {
              message = "Copying and training a model.";
            }
            item.predictorId = predictorId;
            var model = item;
            Predictors.doModelAction(predictorId, item.model_id, 'upsertFeedback').success(function (resp) {
              var updatedModels = resp.data.list;

              // refresh if new models returned
              for (var modelIdx in updatedModels) {
                if (_.pluck($scope.items, 'id').indexOf(updatedModels[modelIdx].id) < 0) {
                  loadModels();
                  break;
                }
              }

              watchModels(updatedModels);
              SystemAlert.success(message + ' ' + item.display_name, 5000);
            });
          }
      };

    function watchModels (models, interval) {
      interval = interval || 1000;
      _(models).each(function (model) {
        (function tick() {
          Predictors.getOneModel(model.predictor, model.id)
            .success(function (res) {
              console.log("Trying to refresh the status of models.");
              res = res.data;
              var progress = res.task_data && res.task_data.progress;
              var isStuck = model.task_data && res.task_data && res.task_data.updated_at === model.task_data.updated_at;
              console.log(res);
              if (progress == null || angular.isNumber(progress) && progress < 100 && !isStuck) {
                $scope.being_retrained = true;
                _.each($scope.items, function (item, i) {
                  if (item.id == model.id) {
                    $scope.items[i].task_data = res.task_data;
                  }
                });
                $timeout(tick, interval);
              } else {
                $scope.being_retrained = false;
                loadModels();
              }
            });
        })();
      });
    }

    $scope.being_retrained = false;
    $scope.$watch('items.length', function (newVal) {
      if (newVal && newVal > 0) {
        var models = _.filter($scope.items, function (item) {
          return item.task_data && item.task_data.progress < 100
        });
        watchModels(models);
      }
    });

    angular.extend($scope, viewModelBase);

    function loadModels() {
      // load all models
      $scope.selectedModels.length = 0;
      Predictors.listModels(predictorId, true).success(function(res) {
        $scope.items = res.data;
        if (!$scope.items.length) return;
        if ($scope.items[0].quality.measure === 'AUC') {
          $scope.qualityDescr = 'The area under the Precision-Recall curve indicates the relationship between the precision of the model (is it correct when it reports a true value) vs. the recall (how many true positives does it pick up).'
        } else if ($scope.items[0].quality.measure === 'RMSE') {
          $scope.qualityDescr = 'The root mean square error is a standard measure of prediction accuracy capturing the difference between the predicted value and the actual value for a dataset.'
        }
      });
    }

    function initialize() {
      loadModels();
      // load predictor
      Predictors.getOne(predictorId).success(function (res) {
        $scope.predictor = res.predictor;
      });
    }

    initialize();
  }
})();