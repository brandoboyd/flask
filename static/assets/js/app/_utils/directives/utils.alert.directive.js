(function () {
  'use strict';

  angular
    .module('slr.utils')
    .directive('slrAlert', systemAlertContainer);

  /**
   * display manual alerts from controllers
   * also handle alerts coming from backend thru HTTP requests
   */
  /** @ngInject */
  function systemAlertContainer($rootScope, SystemAlert, toaster) {
    var state = {
        messages: []
      },
      template = '<div>' +
        '<ark-toaster toaster-options="alertOptions"></ark-toaster>' +
        '</div>';

    return {
      restrict: "AE",
      template: template,
      replace: true,
      link: function (scope) {
        scope.alertOptions = {
          'time-out': 5000,
          'close-button': true,
          'position-class': 'toast-top-right'
        };

        $rootScope.$on(SystemAlert.MESSAGE_EVENT, function (event, data) {
          var newMessages = data.messages;
          if (!angular.isArray(newMessages)) {
            newMessages = [newMessages];
          }
          state.messages.push.apply(state.messages, newMessages);
          _.each(newMessages, function (alert) {
            toaster.pop(alert.type, alert.message, '', data.timeout || 2000);
          });
        });
      }
    }
  }
})();