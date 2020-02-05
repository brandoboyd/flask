(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('CreateEditPredictorsModelCtrl', CreateEditPredictorsModelCtrl);

  /** @ngInject */
  function CreateEditPredictorsModelCtrl($location, $routeParams, $scope, PredictorsRest, SystemAlert) {
    var Predictors = new PredictorsRest();
    var predictorId = $routeParams.predictorId,
        modelId = $routeParams.id;
    var viewModelBase = {
      title: modelId ? 'Update' : 'Create',
      item: {
        display_name: '',
        description: '',
        model_type: '',
        action_features: [],
        context_features: [],
        train_data_percentage: 50,
        min_samples_thresould: 1
      },
      redirectAllHref: function () {
        return '/predictors/' + predictorId + '/models/';
      },
      redirectAll: function () {
        $location.path(this.redirectAllHref());
      },
      save: function () {
        var _params = _.pick($scope.item, 'display_name', 'description', 'model_type', 'context_features', 'action_features', 'train_data_percentage', 'min_samples_thresould');

        console.log('SAVE', _params);
        if (modelId) {
          //update
          Predictors.updateModel(predictorId, modelId, _params)
            .success(function successCallback(response) {
              $scope.redirectAll();
            });
        } else {
          //create
          return Predictors.saveModel(predictorId, _params).success(function () {
            SystemAlert.success('Model saved', 5000);
            //$scope.form.$setPristine();
            $scope.redirectAll();
          });
        }
      }
    };

    angular.extend($scope, viewModelBase);

    function initialize() {
      if (modelId) {
        Predictors.getOneModel(predictorId, modelId)
          .success(function (item) {
            $scope.item = item.data;
          })
      }
      
      // load predictor template
      Predictors.getDefaultPredictor()
        .success(function (res) {
          $scope.template = res.template;
        });

      // load predictor
      Predictors.getOne(predictorId).success(function (res) {
        $scope.predictor = res.predictor;
      });
    }


/*
    $scope.updateSplit = function(val) {
      $scope.train_data_percentage = val;
    }
*/
    initialize();
  }
})();