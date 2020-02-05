(function () {
  'use strict';

  angular
    .module('slr.services')
    .factory('AppStore', AppStore);

  /** @ngInject */
  function AppStore($rootScope, ChannelsService) {
    var AppStore = {};
    AppStore.read = function (settings) {
      return amplify.store(settings)
    };
    AppStore.store = function (name, obj) {
      amplify.store(name, obj, {expires: 86400000})
    };
    $rootScope.$on(ChannelsService.ON_CHANNELS_SELECTED, function () {
      var channel = ChannelsService.getSelected();
      if (channel.parent_id) {
        AppStore.store('service_channel', channel);
      }
      AppStore.store('common_channel', channel);
    });
    return AppStore;
  }
})();