(function () {
  'use strict';

  angular
    .module('slr.configure')
    .config(function ($routeProvider) {
      $routeProvider
        .when('/labels/all', {
          templateUrl: '/partials/labels/labels',
          controller: 'ContactLabelsCtrl',
          name: 'labels'
        })
        .when('/labels/edit', {
          templateUrl: '/partials/labels/edit',
          controller: 'CreateEditLabelCtrl',
          name: 'labels'
        })
        .when('/labels/edit/:label_id', {
          templateUrl: '/partials/labels/edit',
          controller: 'CreateEditLabelCtrl',
          name: 'labels'
        })
    })
})();