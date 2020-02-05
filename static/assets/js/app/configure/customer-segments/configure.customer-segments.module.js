(function () {
  'use strict';

  angular
    .module('slr.configure')
    .config(function ($routeProvider) {
      $routeProvider
        .when('/customer_segments', {
          templateUrl: '/partials/customer_segments/list',
          controller: 'CustomerSegmentListCtrl',
          name: 'customer_segments'
        })
        .when('/customer_segments/edit/:id?', {
          templateUrl: '/partials/customer_segments/edit',
          controller: 'CreateEditCustomerSegmentCtrl',
          name: 'customer_segments'
        })
    })
})();