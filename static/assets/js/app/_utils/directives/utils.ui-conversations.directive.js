(function () {
  'use strict';

  angular
    .module('slr.utils')
    .directive('uiConversations', uiConversations);

  /** @ngInject */
  function uiConversations($modal, $rootScope, ChannelsService, ConversationService, PostFilter, SmartTags) {
    return {
      template: '<a href="" ng-click="getConversation()" ng-show="item.has_conversation"><span class="icon-chat-oval"></span> View Conversation</a>',
      replace: true,
      scope: {
        item: "=uiConversations",
        activeTag: "=selectedTagFilter"
      },
      link: function (scope, elm, attrs) {
        scope.getConversation = function () {
          var post_id = scope.item.id_str;
          var response_id = attrs.responseId;

          var channel_id = ChannelsService.getSelectedId();
          ConversationService.list_by_post(post_id, channel_id).then(function (res) {
            scope.openDialog(res, response_id, post_id);
          })
        };
        scope.openDialog = function (list, response_id, post_id) {
          var d = $modal.open({
            backdrop: true,
            keyboard: true,
            templateUrl: '/partials/conversations/convModal',
            //resolve: { item: function(){ return angular.copy(scope.item) }},
            controller: function ($scope) {
              $scope.posts = list;
              $scope.modal_title = 'Conversation';
              $scope.unreplied_posts = _.filter(list, function (el) {
                return el.filter_status != 'actual'
              });
              $scope.default_profile_url = "/static/assets/img/default_profile2.png";
              // Post actions
              var postStatusChanged = function (post) {
                post.is_disabled = true;
              };
              $scope.rejectPost = PostFilter.command('reject', postStatusChanged);
              $scope.starPost = PostFilter.command('star', postStatusChanged);

              $scope.$on(SmartTags.ON_POST_TAGS_REMOVED, function (event) {
                if (event.defaultPrevented != true) {
                  var tag_removed = event.targetScope.tag;
                  var all_tags = _.flatten(_.pluck($scope.unreplied_posts, 'smart_tags'));
                  var same_tag = _.find(all_tags, function (tag) {
                    return tag.id == tag_removed.id
                  })
                  if (typeof same_tag == 'undefined') {
                    if (tag_removed.id == scope.activeTag.id) {
                      //pass along the tag which was removed because we are no longer in the tag scope here
                      $rootScope.$broadcast(SmartTags.ON_POST_TAGS_REMOVED, response_id, post_id, tag_removed, true);
                      $scope.close();
                    }
                  }
                }
              });

              $scope.close = $scope.$close;

              (function killBackgroundScroll(dialog) {
                // workaround for Chrome
                if (!dialog) {
                  return;
                }

                var $body = $('body'),
                  overflowVal = 'visible',
                  scrollTop = $body.scrollTop(),
                  scrollTo = function (px) {
                    $body.scrollTop(px);
                    //$body.scrollTo(px, {duration:0});
                  };

                dialog.opened.then(function suppressScroll() {
                  $body.css({'overflow': 'hidden'});
                  setTimeout(function () {
                    scrollTo(scrollTop);
                    $body.find('.modal-backdrop').bind('click', returnScroll);

                    $scope.scrollToPost = _.find(list, function (item) {
                      return item.id_str === post_id;
                    });
                    $scope.scrollToIndex = _.indexOf(list, $scope.scrollToPost);
                  }, 0);
                });
                dialog.result.then(returnScroll);

                function returnScroll() {
                  $body.css({'overflow': overflowVal});
                  scrollTo(scrollTop);
                  $body.find('.modal-backdrop').unbind('click', returnScroll);
                }
              }(d));

            }
          });

        }
      }
    }
  }
})();