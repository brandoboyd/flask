(function () {
  'use strict';

  angular
    .module('slr.services', [
      'slr.models',
      'slr.utils',
      'ngResource' // TODO: this is only for the time being. Move $http/$resource to models
    ]);
})();