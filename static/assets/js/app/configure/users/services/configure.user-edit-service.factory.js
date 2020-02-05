(function () {
  'use strict';

  angular
    .module('slr.configure')
    .factory('UserEditService', UserEditService);

  /** @ngInject */
  function UserEditService($resource) {
    return $resource('/users/edit/json', {}, {
      query: {method: 'GET', isArray: false},
      update: {method: 'PUT'}
    });
  }
})();