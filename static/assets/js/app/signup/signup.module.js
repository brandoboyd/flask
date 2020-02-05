(function () {
  'use strict';
  angular
    .module('signup', [])
    .config(function($locationProvider) {
      $locationProvider.html5Mode(true);
    })
})();


