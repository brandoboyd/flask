(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('AddUserCtrl', AddUserCtrl);

  /** @ngInject */
  function AddUserCtrl($scope, $location, $routeParams, $http, SystemAlert) {
    $scope.accountId = $routeParams.acct_id;

    $scope.title = 'Add existing user';

    $scope.save = function () {
      $http({
        method: 'POST',
        url: '/users/add_to_account/json',
        data: {user: $scope.user}
      }).success(function () {
        $location.path('/users/' + $scope.accountId);
        SystemAlert.success("User was added to account!", 4000);
      }).error(function onError(res) {
        SystemAlert.error(res.message);
      });
    };

    $scope.list = function () {
      $location.path('/users/' + $scope.accountId);
    };

  }
})();