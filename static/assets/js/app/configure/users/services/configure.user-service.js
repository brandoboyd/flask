(function () {
  'use strict';

  angular
    .module('slr.configure')
    .factory('UserService', UserService);

  /** @ngInject */
  function UserService($http) {
    var sharedService = {};

    sharedService.setPassword = function (email, password, callback) {
      return $http.post('/users/' + email + '/password',
        $.param({password: password}),
        {headers: {'Content-Type': 'application/x-www-form-urlencoded'}}).success(callback);
    };
    sharedService.listAvailableUsers = function (callback) {
      return $http.get('/users/json',
        {headers: {'Content-Type': 'application/x-www-form-urlencoded'}}).success(callback);
    };
    sharedService.getUserByEmail = function (email, callback) {
      return $http.get('/users/edit/json?email=' + email,
        {headers: {'Content-Type': 'application/x-www-form-urlencoded'}}).success(callback);
    };
    sharedService.setCurrentAccount = function () {
    };

    return sharedService;
  }
})();