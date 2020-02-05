(function () {
  'use strict';

  angular
    .module('slr.services')
    .factory('popOver', popOver);

  // TODO:??????????????????????
  /** @ngInject */
  function popOver() {
    var pop;
    return {
      get: function () {
        return pop;
      },
      set: function (obj) {
        pop = obj
      }
    }
  }
})();