(function () {
  'use strict';

  angular
    .module('slr.models')
    .factory('TrackingChannel', TrackingChannel);

  // TODO: need to be refactored
  /** @ngInject */
  function TrackingChannel($resource) {
    return $resource('/tracking/:what/json', {what: '@what'}, {
      add_keyword: {method: 'POST', params: {what: 'keywords'}, isArray: false},
      add_skipword: {method: 'POST', params: {what: 'skipwords'}, isArray: false},
      add_watchword: {method: 'POST', params: {what: 'watchwords'}, isArray: false},
      add_username: {method: 'POST', params: {what: 'usernames'}, isArray: false},
      add_language: {method: 'POST', params: {what: 'languages'}, isArray: false},
      remove_keyword: {method: 'DELETE', params: {what: 'keywords'}, isArray: false},
      remove_skipword: {method: 'DELETE', params: {what: 'skipwords'}, isArray: false},
      remove_watchword: {method: 'DELETE', params: {what: 'watchwords'}, isArray: false},
      remove_username: {method: 'DELETE', params: {what: 'usernames'}, isArray: false},
      remove_language: {method: 'DELETE', params: {what: 'languages'}, isArray: false},
      get_keywords: {method: 'GET', params: {what: 'keywords'}, isArray: false},
      get_skipwords: {method: 'GET', params: {what: 'skipwords'}, isArray: false},
      get_watchwords: {method: 'GET', params: {what: 'watchwords'}, isArray: false},
      get_usernames: {method: 'GET', params: {what: 'usernames'}, isArray: false},
      get_languages: {method: 'GET', params: {what: 'languages'}, isArray: false}
    });
  }
})();