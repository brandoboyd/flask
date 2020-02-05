angular.module('app_state_listen', ['slr.components', 'listen'])
    .factory('AppState', ['$rootScope', 'ChannelsService', 'FilterService', 'Posts', 'PlotTypes', 'AppStore',
        function($rootScope, ChannelsService, FilterService, Posts, PlotTypes, AppStore) {


            $rootScope.section_settings = '';
            $rootScope.settings = {};

            $rootScope.$watch('global_section', function(section) {
                $rootScope.section_settings = 'settings' + section;
                $rootScope.settings = AppStore.read($rootScope.section_settings) ?
                    AppStore.read($rootScope.section_settings) : {};
                //console.log($rootScope.settings);
            });

            $rootScope.$on(ChannelsService.ON_CHANNELS_SELECTED, function(){
                $rootScope.settings.channel = ChannelsService.getSelected();
                AppStore.store($rootScope.section_settings, $rootScope.settings);
            });

            return {
                read : AppStore.read
            }

        }
    ])
    .value('uiJqConfig', {

        // The Tooltip namespace
        tooltip: {
            animation: false,
            placement: 'bottom',
            container: 'body'
        }

    });

angular.module('voc', ['ui.select2',
                      'ui.scrollfix',
                      'slr.components',
                      'ngResource',
                      'ngSanitize',
                      'infinite-scroll']).controller('VOCCtrl',

function VOCCtrl ($log, $scope, $rootScope, $resource, $window, $timeout, $location, $sce, $http, ChannelsService, FilterService, SmartTag, SmartTags, Posts, PostsExport) {

  /* Channels Selector */
  $scope.channels = [];
  $scope.channel  = null;
  $scope.filtered_tag_id = null;
  var getStoredChannelId = function() {
      var ch = amplify.store('voc_channel') || null;
      //var ch = null;
      return ch ? ch.id : null;
  };

  $scope.total_posts = 0;
  $scope.offset = 0;
  $scope.limit = 15;
  $scope.column_names = ['Promoter', 'Passive', 'Detractor'];
  $scope.column_colors = ["green", "yellow", "red"];
  $scope.channel_id = getStoredChannelId();

  $scope.numberStyle = function(num, classifier){
    var color = "black";
    low_num = num < 5.0;
    hl_class = _.contains(["Promoter", "Detractor"], classifier);
    if (hl_class == true) {
      color="white";
    }
    if (low_num == true) {
      color="black";
    }
    return {'color': color};
  };

  $scope.exportPosts = function() {
    return PostsExport.exportPosts(angular.extend(
      getSearchParams(), {smartTag: $scope.smart_tag.selected}));
  };

  $scope.changeChannel = function(ch){
    $scope.channel = ch;
  };

  $scope.$watch('channel', function(newVal, oldVal) {
      //console.log("scope.channel watch -- newVal: "+newVal+ ". OldVal: "+oldVal);
      //$scope.params.channel_id = $scope.channel ? $scope.channel.id : null;

      if($scope.channel != null){
        //console.log($scope.params.channel_id);
        ChannelsService.setSelected($scope.channel);
        //Store selected channel
        amplify.store('voc_channel', $scope.channel, {expires:86400000})
        //fired to store the selected channel
        $scope.$emit("channel_selected");
        //reload the stats
        $scope.resetPaging();
        loadStats();
      }
    });

  var noChannelErrMessage = { message : "You have access to no VOC channel. All views will be disabled.", type:'error'};

  $scope.$watch('smart_tag.selected', function(newVal, oldVal) {
        if (newVal != oldVal) {
            loadStats();
            if ($scope.activeSection.details) {
              $scope.resetPaging();
              var params = getSearchParams();
              if (params == null) {
                  return;
              }
              debounced_get_details(params, $scope.activeSection.details);
            };
        }
    });

  ChannelsService.getAll('inbound', false, true).then(function(d){
    //display channels of VOC platform only
    $scope.channels = _.filter(d, function(ch) { return ch.platform == 'VOC'});
    //switch to stored one if exists or use the first one in the list
    $scope.channel = _.find($scope.channels, function(el) { return el.id == getStoredChannelId() }) || $scope.channels[0]
  });

  $scope.currentDate = FilterService.getSelectedDateRangeName();

  // Date range filtering
  var formatDate = function (date) {
    return dateFormat(date, "yyyy-mm-dd HH:MM:ss", true);
  };

  $scope.$on(FilterService.DATE_RANGE_CHANGED, function() {
    $scope.currentDate = FilterService.getSelectedDateRangeName();
    var selectedPeriod = FilterService.getDateRangeObj();
    $scope.from = formatDate(selectedPeriod.from);
    $scope.to   = formatDate(selectedPeriod.to);

    loadStats();
    if ($scope.activeSection.details) {
      $scope.resetPaging();
      var params = getSearchParams();
      if (params == null) {
          return;
      }
      debounced_get_details(params, $scope.activeSection.details);
    };
  });

  //services classes for ACTIONS - here we set REST endpoints
  var Stats = $resource('/voc/crosstab/json', {}, {
      fetch: {method:'POST' , isArray:false}
  });

  var getDetails = function(params, isByTab) {
    var url = '/posts/crosstag/json';

    if ($scope.activeSection.details) {
        // We might need to overwrite some things
        if ($scope.filtered_tag_id) {
            params.channel_id = $scope.filtered_tag_id.title.match(/untagged/i) ? $scope.channel.id : $scope.filtered_tag_id.id;
        } else {
            params.channel_id = $scope.channel.id;
        }

        if ($scope.smart_tag && $scope.smart_tag.selected) {
            // If specific filtering was done there are two paths
            params.response_type = [$scope.smart_tag.selected];
        } else {
            params.response_type = [];
        }
    }

    $scope.arePostsDisabled = true;
    $scope.showLoader = true;

    $http({
        method : 'POST',
        url    : url,
        data   : params
    }).then(function (res) {

        $timeout(function() {
            $scope.showLoader = false;
        }, 500);
        $scope.arePostsDisabled = false;

        var inserted = false;
        _.each(res.data.list, function(item) {
            var e = _.find($scope.posts, {'id_str': item.id_str});
            if (e === undefined) {  // HACK for now to keep track of has_more_posts
                inserted = true;
                $scope.posts.push(item);
            }
        });

        //$scope.has_more_posts = res.are_more_posts_available;
        $scope.has_more_posts = true; // HACK FOR NOW
        if (!inserted) {
            $scope.has_more_posts = false;
        }

        $scope.offset = $scope.posts.length;
    });
  };

  var debounced_get_details = _.debounce(getDetails, 300);

  $scope.resetPaging = function() {
    $scope.limit = 15;
    $scope.offset = 0;
    $scope.has_more_posts = true;
    $scope.posts = [];
  }

  $scope.loadMore = function() {
    if ($scope.has_more_posts) {
      debounced_get_details(getSearchParams(),$scope.activeSection.details);
    }
  };

  $scope.isDetailsByTab = false;
  var getSearchParams = function() {
        var channel_id = $scope.channel ? $scope.channel.id : getStoredChannelId();
        var intentions  = FilterService.getIntentionsParams();
        var topics      = []
        var statuses    = FilterService.getPostStatusesParams();
        var level       = FilterService.getSelectedGraphLevel();
        var interval    = null;
        var from        = interval ? formatDate(interval.from) : $scope.from;
        var to          = interval ? formatDate(interval.to)   : $scope.to;
        var params = {
            agents        : null,
            intentions    : intentions,
            topics        : topics,
            statuses      : statuses,
            sort_by       : "time",
            thresholds    : {intention:0, influence:0, receptivity:0},
            from          : from,
            to            : to,
            level         : level
        }

        if($scope.activeSection.details) {
            if ($scope.filtered_tag_id) {
                params.channel_id = $scope.filtered_tag_id.title.match(/untagged/i) ? $scope.channel.id : $scope.filtered_tag_id.id;
            } else {
                params.channel_id = $scope.channel.id;
            }

            if ($scope.smart_tag && $scope.smart_tag.selected) {
                params.response_type = $scope.smart_tag.selected;
            } else {
                params.response_type = [];
            }

          if (params.channel_id == null) {
              console.log(noChannelErrMessage);
              //$rootScope.$emit('SystemAlert.MESSAGE_EVENT', { messages: noChannelErrMessage});
              return; // No point to continue
          }
          params.limit  = $scope.limit;
          params.offset = $scope.offset;
        }

        return params;
    };


  $scope.posts = [];
  $scope.smart_tags = [];
  $scope.smart_tag_data = [];
  $scope.column_tags = [];
  $scope.nps_horizontal_bars = [
      {title: 'Promoter', class: 'success-back'},
      {title: 'Passive', class: 'ongoing-back'},
      {title: 'Detractor', class: 'error-back'}
  ];



  var getCrosstabParams = function() {
    var channel_id = $scope.channel ? $scope.channel.id : getStoredChannelId();
    if (channel_id == null){
        console.log(noChannelErrMessage);
        //$rootScope.$emit('SystemAlert.MESSAGE_EVENT', {messages: noChannelErrMessage});
        return; // No point to continue if we don't have a channel
    }
    var interval    = null;
    var from        = interval ? formatDate(interval.from) : $scope.from;
    var to          = interval ? formatDate(interval.to)   : $scope.to;
    return {
            'channel_id':   channel_id,
            'response_type': [],
            'from':         from,
            'to':           to,
            'thresholds':   {'intention': 0.0},
            'row_tag_ids':  null,
            'dynamic_sort': true
    };
  };

    $scope.getTooltip = function(tag, barTitle) {
        var counts = tag.counts[barTitle];
        var percent = (tag.percentages[barTitle])? tag.percentages[barTitle].toFixed(1) : 0.0;

        return '<b>' + barTitle + '</b><br/>' + counts + ' counts (' + percent + '%)'
    };

  $scope.filterByTag = function(tag) {
      if (tag.title == 'Totals') {
          // Should be same as a switch to details page
          $scope.switchTab('details');
      } else {
          if (tag.title == 'Untagged Posts') {
              $scope.filtered_tag_id = {title : "untagged"};
              $scope.switchTab('details');
          } else {
              if (tag.tag_id != null) {
                 $scope.filtered_tag_id = {id: tag.tag_id, title: tag.title};
                 $scope.switchTab('details');
              }
          }
      }
  }

  $scope.clearFilteredTag = function() {
    $scope.filtered_tag_id = null;
    loadStats();
    if ($scope.activeSection.details) {
        $scope.resetPaging();
        var params = getSearchParams();
        if (params == null) {
            return;
        }
        debounced_get_details(params, $scope.activeSection.details);
    }
  };

  $scope.activeSection = {
    share   : true,
    details : false
  }

  $scope.isActive = function(type) {
    return $scope.activeSection[type]
  };

  $scope.switchTab = function(type) {
    if (type == 'details') {
      $scope.isDetailsByTab        = true;
      $scope.activeSection.details = true;
      $scope.activeSection.share   = false;
      $scope.resetPaging();
      var params = getSearchParams();
      if (params == null) {
          return;
      }
      debounced_get_details(params, $scope.activeSection.details);
    } else {
      $scope.filtered_tag_id = null;
      $scope.isDetailsByTab        = false;
      $scope.activeSection.details = false;
      $scope.activeSection.share   = true;
      loadStats();
    }
  };


  $scope.getPosts = function(tag, col_lbl) {
    var col_tag = _.find($scope.smart_tags, function(el) { return el == col_lbl});
    $scope.smart_tag = {'selected' : col_tag};
    var row_tag_id = tag.tag_id ? tag.tag_id : (tag.title.match(/untagged/i) ? 'untagged' : 'totals');
    if (row_tag_id != 'totals') {
        $scope.filtered_tag_id = {id : row_tag_id, title : tag.title} ; // Keep state sticky.
    }
    $scope.switchTab('details');
  }


  $scope.$on('channel_selected', function(evnt) {
    var channel = evnt.targetScope.channel;
    //loadSmartTags(channel.id);
  });


  var loadStats = _.debounce(function() {
    //console.log($scope.params);
    //var params = _.extend({}, $scope.params);
    var params = getCrosstabParams();
    if (params == null) {
        return;
    }
    //console.log(params);
    if ($scope.smart_tag && $scope.smart_tag.selected != null) {
        params['response_type'] = [$scope.smart_tag.selected];
    }

    if (true) {
      var loader = jQuery("#loader");
      var backdrop = jQuery("#loader-backdrop");

      loader.show();
      backdrop.show();

      Stats.fetch(params, function(res){
          $scope.smart_tag_data = res.list;
          $scope.total_posts = res.total;
          $scope.smart_tags = res.column_names;
          loader.hide();
          backdrop.hide();
          //$scope.emit('ON_COMMENTS_LOADED');
      });
    }
  }, 100);

  $scope.isTagEmpty = function(tag){
    // Do not show empty row tags
    return tag.total == 0;
  }

  $scope.isDataEmpty = function(){
    return $scope.total == 0;
  }

});
