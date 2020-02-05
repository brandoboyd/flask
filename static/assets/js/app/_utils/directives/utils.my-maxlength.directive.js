(function () {
  'use strict';

  angular
    .module('slr.utils')
    .directive('myMaxlength', myMaxLength);

  function myMaxLength() {
    return {
      require: 'ngModel',
      link: function (scope, element, attrs, ngModelCtrl) {
        var maxlength = Number(attrs.myMaxlength);

        function fromUser(text) {
          if (text && text.length > maxlength) {
            var transformedInput = text.substring(0, maxlength);
            ngModelCtrl.$setViewValue(transformedInput);
            ngModelCtrl.$render();
            ngModelCtrl.$overflow = true;
            return transformedInput;
          }
          ngModelCtrl.$overflow = false;
          return text;
        }

        ngModelCtrl.$parsers.push(fromUser);
      }
    };
  }
})();