(function () {
  'use strict';

  angular
    .module('slr.utils')
    .directive('arkSwitch', arkSwitch);

  /** @ngInject */
  function arkSwitch() {
    return {
      restrict: 'E',
      templateUrl: '/static/assets/js/app/_utils/directives/ark-switch/utils.ark-switch.directive.html',
      scope: {
        switchModel: '=',
        switchId: '=',
        switchOn: '=',
        switchOff: '=',
        disabledCase: '='
      }
    }
  }
})();