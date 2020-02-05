(function () {
  'use strict';

  angular
    .module('slr.configure')
    .config(function ($routeProvider) {
    $routeProvider
      .when('/password/:email', {
        templateUrl: '/partials/users/profile',
        controller: 'PasswordCtrl',
        name: 'password'
      })
  })
})();