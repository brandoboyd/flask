(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('FunnelsListCtrl', FunnelsListCtrl);

  /** @ngInject */
  function FunnelsListCtrl($scope, JourneyFunnelsRest, JourneyTypesRest) {
    var JourneyFunnels = new JourneyFunnelsRest();
    var JourneyTypes = new JourneyTypesRest();
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
    $scope.selectRow = function (selected) {
      var found = _.find($scope.selected, {id: selected.id});

      if (found) {
        _.remove($scope.selected, selected)
      } else {
        $scope.selected.push(selected)
      }
    };

    JourneyTypes.list().success(function (types) {
      $scope.journeyTypes = types.data;

      var journeyStages = [];
      _.each($scope.journeyTypes, function (type) {
        JourneyTypes.getStages(type.id)
          .success(function (stage) {
            journeyStages.push(stage.data);
            if (journeyStages.length === $scope.journeyTypes.length) {
              $scope.journeyStages = journeyStages;
            }
          });
      });
    });

    JourneyFunnels.list().success(function (res) {
      $scope.items = res.data;
      _.each($scope.items, function (item) {
        var journeyType = _.find($scope.journeyTypes, {'id': item.journey_type});
        if (journeyType) item.journeyTypeName = journeyType.display_name;
      });
    });

    $scope.remove = function () {
      _.each($scope.selected, function (item) {
        JourneyFunnels.remove(item.id).success(function () {
          _.remove($scope.items, {id: item.id});
        });
      });
    };
  }
})();