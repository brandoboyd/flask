(function () {
  'use strict';

  angular
    .module('slr.utils')
    .directive('tagAssignment', tagAssignment);

  /** @ngInject */
  function tagAssignment(SmartTags, ChannelsService) {
    var validatePostTag = function (elm, scope, removeClassName) {
      elm.find('div').on('click', function () {
        SmartTags.addPostTags(
          scope.channelId, scope.postId, scope.tag.id)
          .then(function () {
            elm.removeClass(removeClassName);
            elm.addClass('starred');
          });
      }); //click
    };
    return {
      scope: {
        tag: "=tagAssignment",
        activeTag: "=",
        channelId: "@",
        postId: "="
      },
      link: function (scope, elm) {
        if (_.isArray(scope.activeTag) ? _.indexOf(scope.activeTag, scope.tag.id) !== -1 : scope.activeTag == scope.tag.id) {
          if (scope.tag.assignment == 'starred') {
            elm.addClass('starred');
          } else if (scope.tag.assignment == 'highlighted') {
            elm.addClass('highlighted');
            validatePostTag(elm, scope, 'highlighted');
          } else {
            elm.addClass('selected');
          }
        } else if (scope.activeTag !== ChannelsService.getSelectedId()) {
          elm.addClass('co-highlighted');
          validatePostTag(elm, scope, 'co-highlighted');
        }
      }
    }
  }
})();