(function () {
  'use strict';

  angular
    .module('slr.utils')
    .directive('emailcheck', emailCheck);

  function emailCheck() {
    var EMAIL_REGEXP = /^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,4}$/;
    var testEmails = function (emails) {
      return _.all(emails.split(/[,;:\s\n\t]+/), function (email) {
        return EMAIL_REGEXP.test(email);
      });
    };
    return {
      restrict: 'A',
      require: 'ngModel',
      link: function (scope, elm, attrs, ctrl) {
        ctrl.$parsers.unshift(function (viewValue) {
          if (!viewValue) {
            ctrl.$setValidity('emailcheck', true);
            return viewValue;
          }
          ctrl.$setValidity('emailcheck', testEmails(viewValue));
          return viewValue;
        });

        scope.$watch(attrs.ngModel, function (val) {
          if (val) {
            ctrl.$setValidity('emailcheck', testEmails(val));
          }
        });
      }
    };
  }
})();