(function () {
  'use strict';

  angular
    .module('slr.services')
    .factory('DialogService', DialogService);

  /** @ngInject */
  function DialogService($rootScope) {
    var watcher = {
      OPEN_DIALOG_EVENT: 'OpenDialogEvent',
      CLOSE_DIALOG_EVENT: 'CloseDialogEvent',
      CLOSE: 'CloseDialogEvent'
    };

    watcher.openDialog = function (data) {
      $rootScope.$broadcast(this.OPEN_DIALOG_EVENT, data);
    };

    watcher.closeDialog = function (data) {
      $rootScope.$broadcast(this.CLOSE_DIALOG_EVENT, data);
    };

    return watcher;
  }
})();