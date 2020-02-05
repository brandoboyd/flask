(function () {
  'use strict';
  angular
    .module('omni')
    .directive('omniSmartTag', omniSmartTag)

  function omniSmartTag() {
    return {
      scope: {
        tag           : '=omniSmartTag',
        resolveTagName: '&',
        targetFacet   : '='
      },
      restrict: 'A',
      templateUrl: '/partials/omni/smart-tags-template',
      link: function (scope, element, attrs, ngModel) {
        scope.selected_tags = _.pluck(_.filter(scope.targetFacet, function(i) {return i.enabled == true}), 'id');
        scope.isActive = false;
        scope.$watch('selected_tags', function(nVal, oVal) {
          if(nVal.length > 0) {
            if (_.indexOf(nVal, scope.tag) != -1) {
              scope.isActive = true;
            } else {
              scope.isActive = false;
            }
          }
        })
      }
    };
  }

})();