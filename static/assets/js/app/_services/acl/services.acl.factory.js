(function () {
  'use strict';

  angular
    .module('slr.services')
    .factory('ACLService', ACLService);

  /** @ngInject */
  function ACLService($http) {
    var sharedService = {};
    var URL = '/acl/json';

    sharedService.getUsersAndPerms = function (data, callback) {
      data.a = 'get';
      return $http.post(URL, data).success(function (data) {
        callback(data.result);
      }).error(function () {
        callback(false);
      });
    };

    sharedService.shareAndSave = function (data, callback) {
      data.a = 'share';
      return $http.post(URL, data).success(function (data) {
        callback(data);
      }).error(function () {
        callback(false);
      });
    };

    return sharedService;
  }
})();