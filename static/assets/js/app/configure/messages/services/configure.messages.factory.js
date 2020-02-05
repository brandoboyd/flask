(function () {
  'use strict';

  angular
    .module('slr.configure')
    .factory('Messages', Messages);

  /** @ngInject */
  function Messages($resource) {
    return $resource('/messages/json', {}, {
      list: {method: 'GET', isArray: false}
    });
  }
})();