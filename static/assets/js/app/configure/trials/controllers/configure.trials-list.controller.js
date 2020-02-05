(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('TrialsListCtrl', TrialsListCtrl);

  /** @ngInject */
  function TrialsListCtrl($scope, $location, SystemAlert, Trial) {
    $scope.filters = {
      status: ''
    };

    $scope.table = {
      sort: {
        predicate: 'start_date',
        reverse: true
      }
    };

    $scope.filterPredicate = function (item) {
      var result = true;
      if ($scope.filters.status) {
        result = result && item.status.toLowerCase() == $scope.filters.status.toLowerCase();
      }
      return result;
    };

    $scope.volClass = function (vol) {
      var colorClass = {
        'green': 'text-success',
        'orange': 'text-warning',
        'red': 'text-important'
      };
      if (vol >= 20000 && vol < 25000) {
        return colorClass.orange;
      }
      if (vol >= 25000) {
        return colorClass.red;
      }
      return colorClass.green;
    };

    $scope.create = function () {
      $location.path('/trials/edit/');
    };

    $scope.openAccountView = function (item) {
      $location.path('/accounts/' + item.account_id);
    };

    $scope.refresh = function () {
      Trial.resource.get({}, function (res) {
        $scope.items = res.items;
      }, function onError() {
        SystemAlert.error("Failed to fetch trials");
      });
    };

    $scope.refresh();
  }
})();