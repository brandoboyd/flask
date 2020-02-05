(function () {
  'use strict';

  angular
    .module('slr.utils')
    .directive('uiSelectTags2', uiSelectTags2);

  function uiSelectTags2() {
    var noFoundMessage = 'Hit Enter or Tab to add a new value';
    return {
      require: '?ngModel',
      link: function (scope, element, attrs, ngModel) {
        var sel = element.select2({
          tags: [], formatNoMatches: function (term) {
            return noFoundMessage
          }
        });
        sel.bind("change", function () {
          ngModel.$setViewValue((sel).select2("val"));
          scope.$apply();
        });

        scope.$watch(attrs.ngModel, function (newVal) {
          if (!newVal) return;
          element.select2({
            tags: newVal, formatNoMatches: function (term) {
              return noFoundMessage
            }
          });
        });
      }
    };
  }
})();