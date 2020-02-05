(function () {
  'use strict';

  angular
    .module('slr.utils')
    .directive('dateIsGreaterThan', dateIsGreaterThan);

  function dateIsGreaterThan() {
    var name = 'dateIsGreaterThan',
      startDate;

    return {
      require: 'ngModel',
      link: function (scope, elm, attrs, ctrl) {
        function isGreater(d1, d2) {
          return !d1 || new Date(d1) > new Date(d2);
        }

        function validateSelf(viewValue) {
          if (isGreater(viewValue, startDate)) {
            ctrl.$setValidity(name, true);
            return viewValue;
          } else {
            ctrl.$setValidity(name, false);
            return undefined;
          }
        }

        function validateStartDate(date) {
          startDate = date;
          ctrl.$setValidity(name, isGreater(ctrl.$modelValue, startDate));
        }

        ctrl.$parsers.unshift(validateSelf);
        scope.$watch(attrs[name], validateStartDate);
      }
    };
  }

})();