(function () {
  'use strict';

  angular
    .module('slr.models')
    .factory('Response', Response);

  // TODO: need to be refactored
  /** @ngInject */
  function Response($resource) {
    return $resource('/commands/:action', {}, {
      star: {method: 'POST', params: {action: "star_response"}, isArray: false},
      unstar: {method: 'POST', params: {action: "unstar_response"}, isArray: false},
      forward: {method: 'POST', params: {action: "forward_response"}, isArray: false},
      follow: {method: 'POST', params: {action: "follow_user"}, isArray: false},
      unfollow: {method: 'POST', params: {action: "unfollow_user"}, isArray: false},
      like: {method: 'POST', params: {action: "like_post"}, isArray: false},
      share: {method: 'POST', params: {action: "share_post"}, isArray: false},
      retweet: {method: 'POST', params: {action: "retweet_response"}, isArray: false},
      skip: {method: 'POST', params: {action: "skip_response"}, isArray: false},
      reject: {method: 'POST', params: {action: "reject_response"}, isArray: false},
      post: {method: 'POST', params: {action: "post_response"}, isArray: false},
      post_response_and_case: {method: 'POST', params: {action: "post_response_and_case"}, isArray: false},
      post_custom: {method: 'POST', params: {action: "custom_response"}, isArray: false},
      post_reply: {method: 'POST', params: {action: "custom_reply"}, isArray: false},
      post_custom_response_and_case: {method: 'POST', params: {action: "post_custom_response_and_case"}, isArray: false}
    });
  }
})();