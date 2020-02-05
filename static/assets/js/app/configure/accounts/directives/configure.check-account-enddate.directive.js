(function () {
  'use strict';

  angular
    .module('slr.configure')
    .directive('checkAccountEndDate', checkAccountEndDate);

  /** @ngInject */
  function checkAccountEndDate() {
    var name = 'checkAccountEndDate',
      packageOption = null;

    return {
      require: 'ngModel',
      link: function (scope, elm, attrs, ctrl) {
        function endDateIsValid(date, packageOption) {
          var now = new Date();
          return (packageOption != 'Trial' || date && new Date(date) > now);
        }

        function validateSelf(viewValue) {
          if (endDateIsValid(viewValue, packageOption)) {
            ctrl.$setValidity(name, true);
            return viewValue;
          } else {
            ctrl.$setValidity(name, false);
            return undefined;
          }
        }

        function validateAccount(acct) {
          packageOption = acct && acct.package;
          ctrl.$setValidity(name, endDateIsValid(ctrl.$modelValue, packageOption));
        }

        ctrl.$parsers.unshift(validateSelf);
        scope.$watch(attrs[name], validateAccount, true);
      }
    };
  }
})();