(function () {
  'use strict';
  
  // TODO: SmartTags, SmartTag, SmartTagForm... just have one SmartTagsService

  angular
    .module('slr.services')
    .factory('SmartTags', SmartTags)
    .factory('MultiChannelTags', MultiChannelTags)
    .factory('SingleEventTags', SingleEventTags)
    .factory('GroupsService', GroupsService)
    .factory('GroupUserService', GroupUserService)
    .factory('SmartTag', SmartTag)
    .factory('SmartTagForm', SmartTagForm);
  
  /** @ngInject */
  function SmartTags($http) {
      var channel_url = "/smart_tags/json";
      var post_url = "/commands/assign_post_tag";
      var multi_post_url = "/commands/assign_tag_multi_post";
      var SmartTags = {
        fetch: function (channel_id, adaptive_learning_enabled) {
          var params = {channel: channel_id};
          if (adaptive_learning_enabled != undefined) {
            params['adaptive_learning_enabled'] = adaptive_learning_enabled;
          }
          var promise = $http({
            method: 'GET',
            url: channel_url,
            params: params
          }).then(function (res) {
            return _.sortBy(_.filter(res.data.list, function (tag) {
              return tag.status == 'Active'
            }), function (item) {
              return item.title.toLowerCase();
            });
          });
          return promise;
        },
        getIntentionsByLabel: function (intentions, selectIntentions) {
          var array = [];
          _.each(intentions, function (intentionLabel) {
            array.push(_.findWhere(selectIntentions, {label: intentionLabel}));
          });
          return _.uniq(array);
        },
        getPostTags: function (channel_id, post_id) {
          var promise = $http({
            method: 'GET',
            url: post_url,
            params: {channel: channel_id, post_id: post_id}
          }).then(function (res) {
            return _.filter(res.data.item, function (tag) {
              return tag.status == 'Active'
            });
          });
          return promise;
        },
        addTagMultiPost: function (channel_id, post_ids, tag_id) {
          var promise = $http({
            method: 'POST',
            url: multi_post_url,
            data: {channel: channel_id, posts: post_ids, tag: tag_id}
          }).then(function (res) {
            return res.data;
          });
          return promise;
        },
        removeTagMultiPost: function (channel_id, post_ids, tag_id) {
          var promise = $http({
            method: 'DELETE',
            url: multi_post_url,
            data: {channel: channel_id, posts: post_ids, tag: tag_id}
          }).then(function (res) {
            return res.data;
          });
          return promise;
        },
        addPostTags: function (channel_id, post_id, tags_ids) {
          var promise = $http({
            method: 'POST',
            url: post_url,
            data: {channel: channel_id, post_id: post_id, ids: tags_ids}
          }).then(function (res) {
            return res.data;
          });
          return promise;
        },
        removePostTags: function (channel_id, post_id, tags_ids, response_id) {
          var promise = $http({
            headers: {'Content-Type': 'mimetype=application/xml'},
            method: 'DELETE',
            url: post_url,
            params: {channel: channel_id, post_id: post_id, ids: tags_ids, response_id: response_id}
          }).then(function (res) {
            return res.data;
          });
          return promise;
        },
        getById: function (tag_id) {
          return $http({
            method: 'GET',
            url: channel_url,
            params: {id: tag_id}
          }).then(function (res) {
            return res.data.item;
          });
        },
        listAll: function (params) {
          return $http({
            method: 'GET',
            url: channel_url,
            params: params
          }).then(function (res) {

            return res.data
          });
        }
      }
      SmartTags.ON_POST_TAGS_REMOVED = 'on_post_tags_removed';
      SmartTags.ON_CONV_TAGS_REMOVED = 'on_conv_tags_removed';
      return SmartTags;
    }
  
  /** @ngInject */
  function MultiChannelTags($http) {
      var tags_url = "/multi_channel_tag/multi";
      var MultiChannelTags = {
        listAll: function (params) {
          return $http({
            method: 'GET',
            url: tags_url,
            params: params
          }).then(function (res) {
            return res.data
          });
        },
        getById: function (tag_id) {
          return $http({
            method: 'GET',
            url: tags_url + '?id=' + tag_id
          }).then(function (res) {
            return res.data.item;
          });
        },
        save: function (tag_data) {
          var promise = $http({
            method: 'POST',
            url: tags_url,
            data: tag_data
          }).then(function (res) {
            return res.data.item;
          });
          return promise;
        },
      }
      return MultiChannelTags;
    }
  
  /** @ngInject */
  function SingleEventTags($http) {
      var tags_url = "/multi_channel_tag/single";
      var SingleEventTags = {
        listAll: function (params) {
          return $http({
            method: 'GET',
            url: tags_url,
            params: params
          }).then(function (res) {
            return res.data
          });
        },
        getById: function (tag_id) {
          return $http({
            method: 'GET',
            url: tags_url + '?id=' + tag_id
          }).then(function (res) {
            return res.data.item;
          });
        },
        save: function (tag_data) {
          var promise = $http({
            method: 'POST',
            url: tags_url,
            data: tag_data
          }).then(function (res) {
            return res.data.item;
          });
          return promise;
        },
      }
      return SingleEventTags;
    }
  
  /** @ngInject */  
  function GroupsService($resource) {
      return $resource('groups/json:groupId', {}, {
        query: {method: 'GET', isArray: false}
      });
    }
    
  /** @ngInject */
  function GroupUserService($resource) {
      return $resource('groups/:action/json', {}, {
        fetchUsers: {method: 'POST', isArray: false, params: {action: 'get_users'}},
        updateUsers: {method: 'POST', params: {action: 'update_users'}}
      });
    }
    
  /** @ngInject */
  function SmartTag($resource) {
      var SmartTag = $resource('/smart_tags/:action/json', {}, {
        update: {method: 'POST', params: {action: 'update'}},
        delete: {method: 'POST', params: {action: 'delete'}},
        activate: {method: 'POST', params: {action: 'activate'}},
        deactivate: {method: 'POST', params: {action: 'deactivate'}}
      });
      SmartTag.ON_SMARTTAG_UPDATE = 'on_smarttag_update';
      SmartTag.LRU_TAG_CHANGED = 'on_lru_changed';

      return SmartTag;
    }
    
  /** @ngInject */
  function SmartTagForm(FilterService, ContactLabelsRest, ChannelsService) {
    
    var ContactLabels = new ContactLabelsRest();
      var SmartTagForm = {};

      SmartTagForm.getIntentions = function () {
        return _.map(FilterService.getIntentions(), function (el) {
          return {display: el.display, label: el.label}
        })
      };
      SmartTagForm.getPostStatuses = function () {
        return _.map(['potential', 'actionable', 'rejected'], function (status) {
          return {display: status, label: status}
        });
      };
      SmartTagForm.getContactLabels = function () {
        return ContactLabels.list().success(function (d) {
          if (!d.list.length) return;
          return _.map(d.list, function (el) {
            return {display: el.title, label: el.id}
          })
        });
      };
      SmartTagForm.getChannels = function () {
        return ChannelsService.getAll('inbound', false, true);
      };
      SmartTagForm.getSmartTagDefaults = function () {
        return {
          influence_score: 0,
          intentions: [],
          keywords: [],
          labels: [],
          usernames: [],
          adaptive_learning_enabled: true,
          alarm_enabled: false,
          groups: [],
          users: [],
          alert: {
            is_active: false,
            posts_limit: 1,
            users: []
          }
        }
      };

      SmartTagForm.getFormTitle = function (form_mode) {
        return {
          'create': 'Create',
          'edit': 'Update'
        }[form_mode];
      };
      return SmartTagForm;
    }
})();