(function () {
  'use strict';

  angular
    .module('slr.utils')
    .factory('SystemAlert', SystemAlert);

  /**
   * Handles error System alerts, e.g. coming from server
   */
  /** @ngInject */
  function SystemAlert($http, $rootScope) {
    function pollErrorCount() {
      return $http({
        method: 'GET',
        url: "/error-messages/count"
      }).then(function (res) {
        if (parseInt(res.data['count']) > 0) {
          return fetchErrorMessages();
        }
      });
    }

    function fetchErrorMessages() {
      return $http({
        method: 'GET',
        url: "/error-messages/json"
      }).then(function (resp) {
        var data = resp.data,
          errors = data['data'],
          messages = [];
        for (var idx = 0; idx < errors.length; idx++) {
          messages.push({
            type: 'error',
            message: errors[idx]['message']
          });
        }
        instance.showMessages(messages);
      });
    }

    var timer = null,
      instance = {
        MESSAGE_EVENT: 'SystemAlert.MESSAGE_EVENT',
        startPolling: function () {
          if (!timer) {
            timer = setInterval(pollErrorCount, 20000);
          }
        },
        stopPolling: function () {
          clearInterval(timer);
          timer = null;
        },
        showMessages: function (msgs, timeout) {
          $rootScope.$emit(this.MESSAGE_EVENT, {messages: msgs, timeout: timeout});
        },

        showLoadingMessage: function () {
          angular.element('#loading').show();
        },
        hideLoadingMessage: function () {
          angular.element('#loading').hide();
        }
      };
    ['error', 'info', 'success', 'warn'].forEach(function (method) {
      instance[method] = function (msg, timeout) {
        this.showMessages({type: method, message: msg}, timeout);
      }.bind(instance);
    });
    instance.log = instance.success;

    instance.startPolling();
    return instance;
  }
})();