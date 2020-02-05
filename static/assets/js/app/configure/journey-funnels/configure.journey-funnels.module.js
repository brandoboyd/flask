(function () {
  'use strict';

  angular
    .module('slr.configure')
    .config(function ($routeProvider) {
      $routeProvider
        .when('/funnels', {
          templateUrl: '/partials/funnels/list',
          controller: 'FunnelsListCtrl',
          name: 'funnels'
        })
        .when('/funnels/edit/:id?', {
          templateUrl: '/partials/funnels/edit',
          controller: 'CreateEditFunnelCtrl',
          name: 'funnels'
        })
    })
})();