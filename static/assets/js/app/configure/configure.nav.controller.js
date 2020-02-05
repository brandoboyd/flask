(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('NavCtrl', NavCtrl);

  /** @ngInject */
  function NavCtrl($scope, $rootScope, $route, AccountsService, $window) {
    $rootScope.$on(AccountsService.ACCOUNTS_EVENT, function () {
      $scope.currentAccount = AccountsService.getCurrent();
    });

    $scope.getScrollHeight = function () {
      return $window.innerHeight - 45;
    };

    $scope.layout = {
      slimscroll: {
        height: $scope.getScrollHeight + 'px',
        width: '210px',
        wheelStep: 25
      }
    };

    $rootScope.$on('$viewContentLoaded', function (e) {
      $scope.current = $route.current.name;
    });

    $scope.getCurrent = function (name) {
      return $scope.current && $scope.current === name ? 'active' : '';
    };
  }
})();