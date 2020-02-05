(function () {
  'use strict';

  angular
    .module('slr.configure')
    .config(function ($routeProvider) {
      $routeProvider
        .when('/tags/all', {
          templateUrl: '/partials/tags/tags',
          controller: 'AllTagsCtrl',
          name: 'tags'
        })
        .when('/tags/edit', {
          templateUrl: '/partials/tags/edit',
          controller: 'CreateEditTagCtrl',
          name: 'tags'
        })
        .when('/tags/edit/:tag_id', {
          templateUrl: '/partials/tags/edit',
          controller: 'CreateEditTagCtrl',
          name: 'tags'
        })
    })
})();