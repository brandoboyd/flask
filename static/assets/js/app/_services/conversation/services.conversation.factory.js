(function () {
  'use strict';

  angular
    .module('slr.services')
    .factory("ConversationService", ConversationService);

  // TODO: this is not factory, this most looks like a model service only
  /** @ngInject */
  function ConversationService($http) {
    var url_by_post = '/conversation/json';
    var url_by_user = '/user_profile/json';
    var ConversationService = {
      list_by_post: function (post_id, channel_id) {
        var promise = $http({
          method: 'GET',
          url: url_by_post,
          params: {'post_id': post_id, 'channel_id': channel_id}
        }).then(function (res) {
          return res.data.list;
        });
        return promise;
      },
      list_by_user: function (channel_id, user) {
        var promise = $http({
          method: 'GET',
          url: url_by_user,
          params: {'channel_id': channel_id, 'user_id': user.id, '_type': user._type}
        }).then(function (res) {
          return res.data.list;
        });
        return promise;
      }
    };
    return ConversationService
  }
})();