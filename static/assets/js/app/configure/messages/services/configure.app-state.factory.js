(function () {
  'use strict';

  angular
    .module('slr.configure')
    .factory('AppState', AppState);

  /** @ngInject */
  function AppState($rootScope) {
    //store filters
    $rootScope.$on('configure_messages_filters_changed', function (evnt) {
      amplify.store('configure_messages_filters', evnt.targetScope.filters);
    });
    return amplify;
  }
})();