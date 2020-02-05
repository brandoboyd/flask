(function () {
  'use strict';

  angular
    .module('slr.configure')
    .factory('Message', Message);

  /** @ngInject */
  function Message($resource) {
    return $resource('/message/:action/json', {}, {
      create: {method: 'POST', params: {action: 'create'}},
      update: {method: 'POST', params: {action: 'update'}},
      remove: {method: 'POST', params: {action: 'delete'}},
      activate: {method: 'POST', params: {action: 'activate'}},
      deactivate: {method: 'POST', params: {action: 'deactivate'}}
    });
  }
})();