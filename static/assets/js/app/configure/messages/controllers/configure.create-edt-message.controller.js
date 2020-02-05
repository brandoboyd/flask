(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('CreateEditMessageCtrl', CreateEditMessageCtrl);

  /** @ngInject */
  function CreateEditMessageCtrl($scope, $location, $routeParams, $q, Message, Messages, ChannelsService, FilterService, SystemAlert, LanguageUtils) {
    /** INIT */
    $scope.params = {};
    $scope.form_mode = null;
    $scope.form_mode = $routeParams.form_mode;
    $scope.message_id = $routeParams.message_id;
    $scope.source_channel_id = $routeParams.source_channel_id; // Keep track where the edit came from.
    $scope.changingChannelIds = [];
    $scope.matchable = newMatchable();
    $scope.fullIntentions = _.map(FilterService.getIntentions(), function (el) {
      return {
        display: el.display,
        label: el.label
      };
    });

    function newMatchable() {
      return {
        intentions: [],
        channels: [],
        creative: '',
        language: '',
        topics: []
      };
    }

    /** ALL LANGUAGES */
    var langPromise = LanguageUtils.fetchSupportedLanguages().then(function (result) {
      $scope.fullLanguages = result;
    });

    ChannelsService.load('inbound', false, true);

    /** ALL CHANNELS */
    var channelsDeferred = $q.defer();
    $scope.$on(ChannelsService.ON_CHANNELS_LOADED, function () {
      channelsDeferred.resolve();
      $scope.fullChannelList = ChannelsService.getList();
    });

    /** OPERATIONS BY MODE STATUS */
    if ($scope.message_id && $scope.form_mode === 'edition') {
      $scope.mode = 'edit';
      Messages.get({id: $scope.message_id}, function (res) {
        /* res.matchable contains only labels, Ids, so we need to operate with them as well */
        $scope.matchable = res.matchable;

        /** INTENTIONS */
        var intentions = [];
        _.each($scope.matchable.intentions, function (intentionLabel) {
          intentions.push(_.findWhere($scope.fullIntentions, {label: intentionLabel}));
        });
        $scope.chosenIntentions = _.uniq(intentions);
        $scope.changingIntentionLabels = _.pluck($scope.chosenIntentions, 'label');

        /** CHANNEL */
        channelsDeferred.promise.then(function () {
          /* $scope.matchable.channels[0] === CHANNEL_ID */
          $scope.chosenChannel = _.findWhere($scope.fullChannelList, {id: $scope.matchable.channels[0]});
          $scope.changingChannelIds = $scope.matchable.channels; // 1 ID
          $scope.channelsChanged();
        });

        /** LANGUAGE */
        langPromise.then(function () {
          $scope.chosenLang = _.findWhere($scope.fullLanguages, {code: $scope.matchable.language});
          $scope.changingLangCode = [$scope.chosenLang.code];
        });
      });
    } else {
      $scope.mode = 'create';
      $scope.chosenIntentions = null;
      $scope.changingIntentionLabels = [];

      $scope.chosenLang = null;
      $scope.changingLangCode = [];

      $scope.chosenChannel = null;
      $scope.changingChannelIds = [];

      $scope.matchable = newMatchable();

      if ($scope.source_channel_id) {
        channelsDeferred.promise.then(function () {
          $scope.matchable.channels = [$scope.source_channel_id];
          $scope.chosenChannel = _.findWhere($scope.fullChannelList, {id: $scope.matchable.channels[0]});
          $scope.changingChannelIds = $scope.matchable.channels;
          $scope.channelsChanged();
        });
      }
    }

    $scope.platform = null;
    $scope.title = {
      'create': 'Create',
      'edit': 'Update'
    }[$scope.mode];

    /** ACTIONS */
    $scope.addIntention = function (intention) {
      $scope.changingIntentionLabels.push(intention.label);
    };
    $scope.removeIntention = function (intention) {
      $scope.changingIntentionLabels.splice($scope.changingIntentionLabels.indexOf(intention.label), 1);
    };
    $scope.addChannel = function (channel) {
      $scope.changingChannelIds = [channel.id];
      $scope.channelsChanged();
    };
    $scope.addLang = function (lang) {
      $scope.changingLangCode = [lang.code];
    };

    $scope.channelsChanged = function () {
      // On each channel change, keep track if we need to track by platform or not
      if ($scope.matchable.channels.length) {
        var channel = null;
        if ($scope.form_mode === 'create') {
          channel = $scope.fullChannelList[0];
        } else {
          // We have a channel selected, filter by that platform.
          channel = _.findWhere($scope.fullChannelList, {id: $scope.matchable.channels[0]});
        }
        $scope.platform = channel.platform;
      } else {
        $scope.platform = null;
      }
    };

    $scope.redirectAllMessages = function (channel_id) {
      if (channel_id) {
        $location.path('/messages/all/' + channel_id);
      } else {
        $location.path('/messages/all');
      }
    };

    $scope.saveButtonDisabled = function () {
      if (!$scope.matchable.creative) {
        return true;
      }
      if (!$scope.changingChannelIds.length) {
        return true;
      }
      return false;
    };

    $scope.save = function () {
      var PostMethod;
      $scope.matchable.intentions = _.uniq($scope.changingIntentionLabels);
      $scope.matchable.channels = $scope.changingChannelIds;
      $scope.matchable.language = $scope.changingLangCode[0];

      if ($scope.mode == 'create') {
        PostMethod = Message.create;
      } else {
        PostMethod = Message.update;
      }

      PostMethod($scope.matchable, function () {
        $scope.redirectAllMessages($scope.changingChannelIds[0]);
      }, function onError(err) {
        SystemAlert.error(err);
      });
    };

  }
})();