(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('ChannelConfigureCtrl', ChannelConfigureCtrl);

  /** @ngInject */
  function ChannelConfigureCtrl($location,
                                $resource,
                                $rootScope,
                                $route,
                                $routeParams,
                                $scope,
                                $window,
                                AccountsService,
                                ChannelsRest,
                                CompoundChannelService,
                                FilterService,
                                SocialService,
                                SystemAlert) {

    var _ChannelsRest = new ChannelsRest();
    var updateData = {};
    $scope.channel_types = [];
    $scope.channel_name = '';
    $scope.channel_description = '';
    $scope.channel_id = null;
    $scope.channel = {};
    $scope.intentions_filter = FilterService.getIntentions();

    $scope.moderated_intention_threshold = 0;
    $scope.auto_reply_intention_threshold = 1;
    $scope.moderated_relevance_threshold = 0;
    $scope.auto_reply_relevance_threshold = 1;

    $scope.twitter_test_option = 'account';
    $scope.twitter_handle = null;

    AccountsService.query({}, function (res) {
      $scope.accounts = _.sortBy(_.pluck(res.data, 'name'), function (item) {
        return item.toLowerCase();
      });
      $scope.accountsObjs = angular.copy(res.data);

      if ($routeParams.account_id) {
        $scope.account = _.find($scope.accountsObjs, function (item) {
          return item.id == $routeParams.account_id;
        });
      } else {
        $scope.account = AccountsService.getCurrent();
      }
    });

    var ChannelTypes = $resource('/configure/channel_types/json', {}, {
      fetch: {method: 'GET', isArray: false}
    });

    $scope.channel_type = null;

    $scope.load = function () {
      var res = ChannelTypes.fetch({}, function () {
        $scope.channel_types = _.sortBy(res.list, 'title');
      }, function onError() {
        SystemAlert.error("Error loading channel types!");
      });

    };

    $scope.$watch('channel_type', function (newValue, oldValue) {
      if ((newValue == 'compound' || newValue == 'service') && newValue != oldValue) {
        CompoundChannelService.prepare();

        $scope.$on(CompoundChannelService.CHANGED, function (event, data) {
          _.forEach(data, function (item) {
            $scope.update_params[item.key] = item.value;
          });
        });
      }
    });


    $rootScope.$on('$viewContentLoaded', function (e) {
      if ($route.current.name == 'channels-no-channels') {
        $scope.isNoChannels = true;
      }
    });

    $scope.$on(SocialService.POPUP_CLOSE, function (evt, data) {
      if (data.type == 'twitter') {
        // popup closed - fetch profile
        $scope.getTwitterProfile();

      } else {
        $scope.getFacebookProfile();

      }
    });

    $scope.getTwitterProfile = function () {
      SocialService.twitterGetProfile($scope.channel_id, function (res) {
        $scope.twitter_profile = res.twitter_profile;
        if ($scope.channel != undefined) {
          if (res.twitter_profile != null) {
            $scope.channel.twitter_handle = res.twitter_profile.screen_name;
          }
          else $scope.channel.twitter_handle = null;
        }
      }, function onError() {
        $scope.twitter_profile = null;
        if ($scope.channel != undefined) $scope.channel.twitter_handle = null;
      });
    };

    $scope.getFacebookProfile = function () {
      SocialService.fbGetProfile($scope.channel_id, function (res) {
        $scope.facebook_profile = res.facebook_profile;
      }, function onError() {
        $scope.facebook_profile = null;
      });
    };


    $scope.twitter_request_token = function () {
      SocialService.twitterRequestToken($scope.channel_id);
    };

    $scope.facebook_request_token = function () {
      SocialService.facebookRequestToken($scope.channel_id);
    };

    $scope.twitter_logout = function () {
      SocialService.twitterLogout($scope.channel_id);
    };

    $scope.facebook_logout = function () {
      SocialService.facebookLogout($scope.channel_id);
    };

    var _channelIds = [];
    $scope.create = function () {
      _ChannelsRest.saveNewChannel({
        type: $scope.channel_type,
        title: $scope.channel_name,
        description: $scope.channel_description,
        account_id: $routeParams.account_id
      }).success(function (res) {
        $location.path('/channels');
        _channelIds.push(res.id);
        if (_.indexOf(['voc', 'emailservice', 'chatservice'],
            $scope.channel_type) !== -1) {
          $location.path('/channels');
        } else {
          $scope.channel_id = res.id;
          $scope.loadChannel(res.id);
        }
      });
    };

    $scope.update_params = {};
    $scope.childScope = null;
    $scope.isAdvancedState = false;
    //need this to get to a child scope, the function is triggered from within ng-switch directive
    $scope.passTheScope = function (scope) {
      $scope.childScope = scope;
    };

    $scope.$watch('channel', function (newVal, oldVal) {
      if (newVal != oldVal) {
        $scope.account = _.find($scope.accountsObjs, function (item) {
          return item.name == $scope.channel.account
        });
        $scope.update_params = {
          channel_id: $scope.channel_id,
          title: $scope.channel.title,
          description: $scope.channel.description,
          account: $scope.channel.account,

          moderated_intention_threshold: $scope.moderated_intention_threshold,
          auto_reply_intention_threshold: $scope.auto_reply_intention_threshold,
          moderated_relevance_threshold: $scope.moderated_relevance_threshold,
          auto_reply_relevance_threshold: $scope.auto_reply_relevance_threshold,

          review_outbound: $scope.channel.review_outbound,
          history_time_period: $scope.channel.history_time_period,
          auto_refresh_followers: $scope.channel.auto_refresh_followers,
          skip_retweets: $scope.channel.skip_retweets,
          auto_refresh_friends: $scope.channel.auto_refresh_friends,
          dispatch_channel: $scope.channel.dispatch_channel,
          grouping_timeout: $scope.channel.grouping_timeout,
          grouping_enabled: $scope.channel.grouping_enabled
//                fb_pull_mode                   : $scope.channel.fb_pull_mode
        }

        if ($scope.channel.is_compound || $scope.channel.is_service) {
          CompoundChannelService.setCompound($scope.channel);
        }
      }
      ;
    }, true);

    var onError = function () {
      SystemAlert.error("No Channels Available");
    };

    $scope.last_item = null;
    
    function isNewService(channel) {
      var id = angular.isString(channel) ? channel : channel.id;
      return _channelIds.indexOf(id) !== -1 && channel.is_service;
    }

    $scope.update = function () {
      return _ChannelsRest.updateConfigureChannel($scope.update_params)
        .success(function (res) {
          if (isNewService(res.item)) {
            $scope.last_item = res.item;
            //SystemAlert.success("Your channel has been created. Genesys Social Analytics has begun gathering posts and comments.", 5000, 'service');
            $window.location.href = '/inbound#/?channel=' + res.item.id + '&isNew';
          } else {
            $location.path('/channels');
            SystemAlert.success("Your reply channel has been created.", 5000, 'account');
          }
        })
        .error(function(res) {
          onError();
        });
    };

    $scope.loadChannel = function (channel_id) {
      return _ChannelsRest.getOne(channel_id)
        .success(function (res) {
          $scope.channel = res.item;
          if (res.item.type == 'EnterpriseTwitterChannel' || res.item.type == 'TwitterChannel') {
            $scope.getTwitterProfile();
          }
          $location.path('/update_channel/' + res.item.id);
        })
        .error(function (res) {
          onError();
        });
    };

    // load at once to populate channel types chooser
    $scope.load();

    //Add this logic for the Advanced element, so it hides the ActionWords field
    $scope.evaluate = function () {
      return $scope.isAdvancedState;
    }
    $scope.evaluateIcon = function () {
      if ($scope.isAdvancedState) {
        return "icon-expand-down";
      }
      else {
        return "icon-expand-right";
      }
    }
    $scope.changeStatus = function () {
      $scope.isAdvancedState = !$scope.isAdvancedState;
    }
  }
})();
