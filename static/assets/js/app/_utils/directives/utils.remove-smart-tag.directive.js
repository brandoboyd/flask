(function () {
  'use strict';

  angular
    .module('slr.utils')
    .directive('removeSmartTag', removeSmartTag);

  /** @ngInject */
  function removeSmartTag(SmartTags, ChannelsService) {
    return {
      scope: {
        item: "=removeSmartTag",
        tag: "=",
        selectedTagFilter: "="
      },
      link: function (scope, elm, attrs) {
        scope.channelId = ChannelsService.getSelectedId();
        elm.on('click', function () {
          var post_id = scope.item.id_str;
          var response_id = attrs.responseId;
          SmartTags.removePostTags(scope.channelId, post_id, scope.tag.id, response_id).then(function (res) {
            scope.item.smart_tags = _.filter(scope.item.smart_tags, function (el) {
              return el.id !== scope.tag.id
            });
            scope.$emit(SmartTags.ON_POST_TAGS_REMOVED, response_id, post_id);
          });
        })
      }
    }
  }
})();