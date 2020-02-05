(function () {
  'use strict';

  angular
    .module('slr.services')
    .factory('Confirm', Confirm);

  /** @ngInject */
  function Confirm($q, $rootScope, PopupService) {
    var popupOptions = {closeAfterAction: true};

    return function (attrs) {
      if (angular.isString(attrs)) {
        attrs = {actionText: attrs};
      }

      var defaults = {
        title: '',
        actionText: 'Are you sure?',
        actionButtonText: 'Yes',
        cancelButtonText: 'No'
      };
      attrs = angular.extend(defaults, attrs);

      var deferred = $q.defer(),
        scope = $rootScope.$new(),
        actionFnName = '__confirmActionFunction',
        cancelFnName = '__confirmCancelFunction';
      scope[actionFnName] = function () {
        deferred.notify({action: 'confirm'});
        deferred.resolve();
      };
      scope[cancelFnName] = function () {
        deferred.notify({action: 'cancel'});
        deferred.reject();
        PopupService.close();
      };

      PopupService.confirm(attrs["title"], attrs["actionText"],
        attrs["actionButtonText"], actionFnName + "()",
        attrs["cancelButtonText"], cancelFnName + "()",
        scope, popupOptions);
      return deferred.promise;
    }
  }
})();