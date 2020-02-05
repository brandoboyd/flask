(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('CreateEditCustomerSegmentCtrl', CreateEditCustomerSegmentCtrl);

  /** @ngInject */
  function CreateEditCustomerSegmentCtrl($routeParams, $scope, CustomerSegmentsRest) {
    var CustomerSegments = new CustomerSegmentsRest();
    var id = $routeParams.id;
    $scope.title = id ? 'Update' : 'Create';
    $scope.item = {};
    $scope.formState = {};

    if (id) {
      CustomerSegments.getOne(id).success(function (res) {
        $scope.item = res.data;
      });
    } else {
      $scope.item = {
        display_name: "",
        description: "",
        locations: [],
        age_range: [],
        account_balance_range: [],
        num_calls_range: [],
      };
    }

    $scope.save = function () {
      $scope.formState.isSaved = false;
      CustomerSegments.save($scope.item).success(function (res) {
        $scope.title = 'Update';
        $scope.item = res.data;
        $scope.formState.isSaved = true;
      });
    };

    $scope.createNewSegment = function () {
      window.location.reload();
    }
  }
})();