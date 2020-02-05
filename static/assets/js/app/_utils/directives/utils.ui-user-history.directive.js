(function () {
  'use strict';

  angular
    .module('slr.utils')
    .directive('uiUserHistory', uiUserHistory);

  /** @ngInject */
  function uiUserHistory($modal, ChannelsService, ConversationService) {
    return {
      template: '<span>\
                        <button ng-show="item.has_history" class="btn btn-xs btn-info"\
                          ng-click="getUserProfile()"\
                          ui-jq="tooltip" title="User History">\
                        <span class="icon-chat-oval"></span></button>\
                        <button ng-hide="item.has_history" class="btn btn-xs disabled"\
                          ui-jq="tooltip" title="No customer history">\
                        <span class="icon-chat-oval"></span></button>\
                        </span>',
      replace: true,
      scope: {
        item: "="
      },
      link: function (scope, elm) {
        scope.getUserProfile = function () {
          var user = scope.item.user;
          var channel_id = ChannelsService.getSelectedId();
          ConversationService.list_by_user(channel_id, user).then(function (res) {
            scope.openDialog(_.flatten(res));
          })
        };

        scope.openDialog = function (list) {
          var d = $modal.open({
            backdrop: true,
            keyboard: true,
            backdropClick: true,
            templateUrl: '/partials/conversations/convModal',
            //resolve: { item: function(){ return angular.copy(scope.item) }},
            controller: function ($scope) {
              $scope.modal_title = "User History";
              $scope.posts = list;
              $scope.default_profile_url = "/static/assets/img/default_profile2.png";
              $scope.close = function (result) {
                $scope.$close(result);
              };
            }
          });

        }
      }
    }
  }
})();