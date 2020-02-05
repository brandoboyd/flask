(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('CustomerSegmentListCtrl', CustomerSegmentListCtrl);

  /** @ngInject */
  function CustomerSegmentListCtrl($scope, CustomerSegmentsRest) {
    var CustomerSegments = new CustomerSegmentsRest();
    $scope.table = {
      sort: {
        predicate: 'display_name',
        reverse: false
      }
    };
    $scope.filters = {
      display_name: ''
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

    var resolveCtrl = function () {
      CustomerSegments.list().success(function (res) {
        $scope.items = res.data;
      });
    };

    $scope.remove = function () {
      _.each($scope.selected, function (item) {
        CustomerSegments.remove(item.id).success(function () {
          _.remove($scope.items, {id: item.id});
        });
      });
    };

    resolveCtrl();
  }
})();