(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('CreateEditFunnelCtrl', CreateEditFunnelCtrl);

  /** @ngInject */
  function CreateEditFunnelCtrl($routeParams,
                                $scope,
                                JourneyFunnelsRest,
                                JourneyTypesRest) {
    var JourneyFunnels = new JourneyFunnelsRest();
    var JourneyTypes = new JourneyTypesRest();
    var funnelId = $routeParams.id;
    $scope.title = funnelId ? 'Update' : 'Create';
    $scope.journeyTypes = {};
    $scope.journeyStages = {};
    $scope.item = {};
    $scope.formState = {};
    $scope.stepItems = [];

    JourneyTypes.list().success(function (types) {
      $scope.journeyTypes = types.data;
      if (!funnelId && $scope.item.journey_type == null && $scope.journeyTypes.length) {
        $scope.item.journey_type = $scope.journeyTypes[0].id;
      }

      var journeyStages = [];
      _.each($scope.journeyTypes, function(type) {
        JourneyTypes.getStages(type.id)
          .success(function(stage) {
            journeyStages.push(stage.data);
            if (journeyStages.length === $scope.journeyTypes.length) {
              $scope.journeyStages = _.flatten(journeyStages);
            }
          });
      });
    });

    $scope.filterByJourneyType = function(item) {
      return item.journey_type_id === $scope.item.journey_type
    };

    if (funnelId) {
      JourneyFunnels.getOne(funnelId).success(function (res) {
        $scope.item = res.data;
        $scope.loadStepItems();
      });
    } else {
      $scope.item = {
        name: '',
        journey_type: null,
        description: '',
        steps: []
      };
    }

    $scope.journeyTypeChanged = function () {
      $scope.stepItems.length = 0;
    };

    $scope.loadStepItems = function () {
      if ($scope.item) {
        $scope.stepItems.length = 0;
        $scope.stepItems = _.map($scope.item.steps, function (step) {
          return {'id': step}
        });
      }
    };

    $scope.addStepItem = function () {
      $scope.stepItems.push({'id': null});
    };

    $scope.removeStepItem = function (index) {
      $scope.stepItems.splice(index, 1);
    };

    $scope.save = function () {
      var isEditMode = !!funnelId;
      $scope.formState.isSaved = false;
      $scope.item.steps = _.remove(_.pluck($scope.stepItems, 'id'), undefined);
      JourneyFunnels.save($scope.item, isEditMode).success(function (res) {
        $scope.title = 'Update';
        $scope.item = res.data;
        $scope.loadStepItems($scope.item);
        $scope.formState.isSaved = true;
      });
    };

    $scope.openNewForm = function () {
      $scope.item = {
        name: '',
        journey_type: null,
        description: '',
        steps: []
      };
      $scope.title = 'Create';
      $scope.loadStepItems($scope.item);
      $scope.formState.isSaved = false;
      $scope.funnelForm.$setPristine();
    }
  }
})();