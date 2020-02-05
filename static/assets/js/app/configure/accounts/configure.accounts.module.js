(function () {
  'use strict';

  angular
    .module('slr.configure')
    .config(function ($routeProvider) {
      $routeProvider
        .when('/accounts', {
          templateUrl: '/partials/accounts/list',
          controller: 'AccountsCtrl',
          name: 'accounts'
        })
        .when('/accounts/:account_id', {
          templateUrl: '/partials/accounts/edit',
          controller: 'AccountEditCtrl',
          name: 'account'
        })
        .when('/new_account', {
          templateUrl: '/partials/accounts/new_account',
          controller: 'AccountsCtrl',
          name: 'account'
        })
    })
    .value('uiJqConfig', {
      datepicker: {
        dateFormat: 'dd/MM/YY'
      }
    })
})();