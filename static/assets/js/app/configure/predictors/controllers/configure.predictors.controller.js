(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('PredictorsCtrl', PredictorsCtrl);

  /** @ngInject */
  function PredictorsCtrl($scope, $location, $q, PredictorsRest, selectedPredictorsService, PredictorService, FilterService, SystemAlert) {

    var Predictors = new PredictorsRest();

    $scope.newCompositePredictor = function() {
      var ids = _.pluck($scope.selected, 'id');
      $location.path('/predictors/new').search({'ids': ids});
    };

    $scope.shouldShowCreateComposite = function () {
      var selected_types = _.pluck($scope.selected, 'predictor_type');
      return $scope.selected.length > 1 && _.indexOf(selected_types, 'Composite Predictor') === -1
    };

    $scope.selectRow = function (selected) {
      var found = _.find($scope.selected, {id: selected.id});

      if (found) {
        _.remove($scope.selected, selected);
      } else {
        $scope.selected.push(selected);
      }
      selectedPredictorsService.setSelected($scope.selected);

      $scope.aggregatedPredictors = filterAggregatedPredictors($scope.selected);
      $scope.deleteAlertMessage = generateDeleteAlert($scope.aggregatedPredictors);
    };

    var loadPredictors = function() {
      var dateRange = FilterService.getDateRange({local: true});

      var params = {
          aggregate: true
      };

      PredictorService.listAllPredictors(params).then(
        function (res) {
          $scope.predictors = res;
          $scope.noPredictors = $scope.predictors.length === 0;
        },
        function () {
          $scope.noPredictors = true;
        }
      );
    };

    $scope.deletePredictor = function () {
      var promises = _.map($scope.selected, function(predictor) {
        return Predictors.removePredictor(predictor.id).then(function() {
          SystemAlert.success(predictor.name + ' has been deleted successfully');
        });
      });

      $q.all(promises).finally(function() {
        // This function also clears the $scope.selected variable.
        activateController();
      });
    };

    $scope.resetClassifier = function (predictor_id) {
      Predictors.doClassifier('reset', predictor_id);
    };

    $scope.retrainClassifier = function (predictor_id) {
      Predictors.doClassifier('retrain', predictor_id);
    };

    $scope.upsertFeedback = function (predictor_id) {
      Predictors.upsertFeedback('upsert_feedback', predictor_id);
    };

    function activateController() {
      $scope.table = {
        sort: {
          predicate: 'name',
          reverse: false
        }
      };
      $scope.filters = {
        name: ''
      };
      $scope.selected = [];
      $scope.aggregatedPredictors = []; // Predictors used by other composite predictors
      $scope.deleteAlertMessage = '';

      loadPredictors();
    }

    function filterAggregatedPredictors(predictors) {
      return _.filter(predictors, function(predictor) {
        return isUsedByCompositePredictor(predictor.id) === true
      });
    }

    // Check if a predictor (to be deleted ) is used by a composite predictor
    // It's not supposed to delete that predictor
    function isUsedByCompositePredictor(predictorId) {
      return _.some($scope.predictors, function(predictor) {
        var aggregatePredictorIds = _.keys(predictor.aggregate_predictors);
        return (aggregatePredictorIds.indexOf(predictorId) > -1);
      });
    }

    function generateDeleteAlert(predictors) {
      var message = [
        'You can not delete the following predictors. They are used by other composite predictors.',
        '<br/>',
        '<br/>',
        '<ul>',
        '</ul>'
      ];

      var names = '';
      _.each(predictors, function(predictor) {
        names += '<li>' + predictor.name + '</li>';
      });

      message.splice(3, 0, names);

      return message.join('');
    }

    activateController();
  }
    
})();
