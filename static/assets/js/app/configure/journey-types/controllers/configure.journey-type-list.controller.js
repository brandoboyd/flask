(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('JourneyTypeListCtrl', JourneyTypeListCtrl);

  /** @ngInject */
  function JourneyTypeListCtrl($location, $scope, SystemAlert, JourneyTypesRest, JourneyFacetConfig) {
    var JourneyTypes = new JourneyTypesRest();
    var init = function () {
      $scope.selected = [];
      $scope.flags = {
        search: '',
        selectedAll: false
      };
      $scope.table = {
        sort: {
          predicate: 'display_name',
          reverse: false
        }
      };
//      $scope.filterPredicate = JourneyFacetConfig.makeFilter($scope); // ???
      $scope.refresh();
    };

    $scope.select = function (selected) {
      if (!selected) {
        // for all selection
        _.each($scope.items, function(each, index) {
          $scope.items[index].selected = !$scope.flags.selectedAll;
        });

        if ($scope.flags.selectedAll) {
          $scope.selected = [];
        } else {
          $scope.selected = _.clone($scope.items);
        }
        $scope.flags.selectedAll = !$scope.flags.selectedAll;
      } else {
        _.each($scope.items, function(each, index) {
          if (selected.id === each.id) {
            var found = _.findWhere($scope.selected, {id: selected.id});
            if (found) {
              _.remove($scope.selected, selected);
            } else {
              $scope.selected.push(selected)
            }
            $scope.items[index].selected = !selected.selected;
          }
        });
        $scope.flags.selectedAll = ($scope.selected.length === $scope.items.length);
      }
    };

    $scope.create = function() {
      $location.path('/journey_types/edit/');
    };

    $scope.refresh = function() {
      JourneyTypes.list().success(function (types) {
        $scope.items = _.map(types.data, function(each) {
          return _.extend(each, {
            status: _.sample(['IN_SYNC', 'OUT_OF_SYNC']),
            selected: false
          });
        });
      });
    };

    $scope.remove = function() {
      _.each($scope.selected, function (item, index) {
        JourneyTypes.remove(item.id).success(function () {
          _.remove($scope.items, function (i) {
            return i.id === item.id
          });
          SystemAlert.info('Journey Type "' + item.display_name + '" removed', 3000);
          if (index === ($scope.selected.length - 1)) {
            $scope.refresh();
          }
        });
      });
    };

    init();
  }
})();