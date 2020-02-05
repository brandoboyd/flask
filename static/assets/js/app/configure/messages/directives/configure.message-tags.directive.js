(function () {
  'use strict';

  angular
    .module('slr.configure')
    .directive('messageTags', messageTags);

  /** @ngInject */
  function messageTags() {
    return {
      require: '?ngModel',
      link: function (scope, element, attrs, ctrl) {
        setTimeout(function () {
          var sel = element.select2({tags: []});

          scope.$watch('matchable.topics', function (newVal, oldVal) {
            sel.select2("val", newVal);
          });

          angular.element(sel).bind("change", function ($event, flag) {
            ctrl.$setViewValue(sel.select2("val"));
          });
        }, 0);
      }
    };
  }
})();