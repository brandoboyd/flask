(function () {
  'use strict';

  angular
    .module('slr.configure')
    .config(function ($routeProvider) {
    $routeProvider
      .when('/user/:email', {
        templateUrl: '/partials/configure/user',
        controller: 'UserEditCtrl',
        name: 'user'
      })
      .when('/users/:acct_id', {
        templateUrl: '/partials/configure/list_users',
        controller: 'UsersListCtrl',
        name: 'account_users'
      })
      .when('/users/edit/:acct_id/', {
        templateUrl: '/partials/users/edit',
        controller: 'CreateUpdateUserCtrl',
        name: 'account_users'
      })
      .when('/users/edit/:acct_id/:user_email', {
        templateUrl: '/partials/users/edit',
        controller: 'CreateUpdateUserCtrl',
        name: 'account_users'
      })
      .when('/users/add/:acct_id/', {
        templateUrl: '/partials/users/add',
        controller: 'AddUserCtrl',
        name: 'account_users'
      })
  })
})();