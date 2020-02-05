(function () {
  'use strict';

  angular
    .module('slr.configure')
    .factory('ContactLabel', ContactLabel);

  /** @ngInject */
  function ContactLabel($resource) {
    return $resource('/contact_label/:action/json', {}, {
      update: {method: 'POST', params: {action: 'update'}},
      add: {method: 'POST', params: {action: 'update'}},
      delete: {method: 'POST', params: {action: 'delete'}},
      activate: {method: 'POST', params: {action: 'activate'}},
      deactivate: {method: 'POST', params: {action: 'deactivate'}}
    });
  }
})();