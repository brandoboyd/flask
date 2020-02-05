(function () {
  'use strict';

  angular
    .module('slr.configure')
    .config(function ($routeProvider) {
      $routeProvider
        .when('/groups/', {
          templateUrl: '/partials/groups/list',
          controller: 'GroupsListCtrl',
          name: 'groups'
        })
        .when('/groups/edit/', {
          templateUrl: '/partials/groups/edit',
          controller: 'CreateUpdateGroupCtrl',
          name: 'groups'
        })
        .when('/groups/edit/:group_id/', {
          templateUrl: '/partials/groups/edit',
          controller: 'CreateUpdateGroupCtrl',
          name: 'groups'
        })
        .when('/groups/edit/:group_id/:tab/', {
          templateUrl: '/partials/groups/edit',
          controller: 'CreateUpdateGroupCtrl',
          name: 'groups'
        })
    })
})();