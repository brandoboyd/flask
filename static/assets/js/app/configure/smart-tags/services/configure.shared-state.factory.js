(function () {
  'use strict';

  angular
    .module('slr.configure')
    .factory('SharedState', SharedState);

  /** @ngInject */
  function SharedState() {
    return {filters: {}};
  }
})();