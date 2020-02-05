angular.module('app_state_engage', ['slr.components'])
    .factory('AppState', ['$rootScope', 'AppStore',
        function(scope, AppStore) {
            //store channel plot type filter
            scope.$on('params_changed', function(evnt) {
                AppStore.store('engage_params', evnt.targetScope.params);
            });
            scope.$on('response_type_changed', function(evnt) {
                AppStore.store('response_type', evnt.targetScope.responseType);
            });
            scope.$on('channel_selected', function(evnt) {
                AppStore.store('engage_channel', evnt.targetScope.channel);
            });
            return {
                read : function(name) {
                    return AppStore.read(name)
                }
            }
        }
    ]);




angular.module('engage',    ['ui.select2',
                             'ngResource',
                             'ngSanitize',
                             'slr.components',
                             'app_state_engage'])
.value('uiJqConfig', {
        // The Tooltip namespace
        tooltip: {
            animation: false,
            placement: 'bottom',
            container: 'body'
        }

});

function ResponsesCtrl(toaster, $scope, $resource, $window, $sce,
                       ChannelsService, FilterService, SmartTag, SmartTags, Response, AppState, AccountsService, SystemAlert) {

    /* Channels Selector */
    $scope.channels = [];
    $scope.channel  = null;

    var getStoredChannelId = function() {
        var ch = AppState.read("common_channel");
        return ch ? ch.id : null;
    };


    ChannelsService.getAll(['inbound','outbound'],false,true).then(function(channels) {
        //don't display service outbound channels at all
        $scope.channels = _.filter(channels, function(el) {
                    return el.parent_id == null && el.is_compound == false ||
                           el.parent_id != null && el.type == 'inbound'  });
        //switch to stored one if exists or use the first one in the list
        $scope.channel = _.find($scope.channels, function(el) { return el.id == getStoredChannelId() }) || $scope.channels[0]
    });


    $scope.changeChannel = function(ch) {
        $scope.channel = ch
    }


    /* smart tags */
    $scope.smart_tags = [];
    $scope.smart_tag = {
        selected : null
    };
    $scope.getChannelId = function() {

        return $scope.smart_tag.selected ? $scope.smart_tag.selected.id
                                         : ChannelsService.getSelectedId();
    };

    $scope.$watch('channel', function(newVal, oldVal) {
       if (newVal != oldVal) {
           $scope.params.channel_id = $scope.channel ? $scope.channel.id : null;
           $scope.params.languages = _.pluck($scope.channel.langs, 'code') || [];
           ChannelsService.setSelected($scope.channel);
           //fired to store the selected channel
           $scope.$emit("channel_selected");
           if (!$scope.shouldShowReview() && $scope.responseType == 'review') {
               $scope.fetchResults('pending');
           }
       }
    }, true);

    // initial sorting
    $scope.predicate = 'post.stats.intention.score';
    // filter params object
    //$scope.params = AppState.read("engage_params") || {};
    $scope.dateRange = FilterService.getDateRange();
    $scope.params = {};
    $scope.params.channel_id = $scope.params.channel_id || null;
    $scope.params.tags = $scope.params.tags || [];
    //$scope.params.intentions = $scope.params.intentions || FilterService.getIntentions();
    $scope.params.intentions = FilterService.getIntentionsParams();
    $scope.params.message_type = FilterService.getMessageTypesParams();
    //$scope.params.date = $scope.dateRangeObj = $scope.params.date || FilterService.getDateRange();
    $scope.delta_responses = -1;


    $scope.params.visibility = {
            pending : false,
            starred : false,
           rejected : false,
          forwarded : false,
             posted : false,
          retweeted : false,
           filtered : false,
           skipped  : false,
           review   : false
    };



    // initial filter thresholds params
    $scope.params.thresholds = {
            "intention" : 0,
            "relevance" : 0
    };
    //$scope.params.sort_by = $scope.params.sort_by || 'date';
    $scope.selected  = [];
    $scope.starred   = [];
    $scope.unstarred = [];


    var shiftDate   = function(date) {
        return FilterService.toUTCDate(date);
    };
    var formatDate  = function(date, shift) {
        var shifted = shift ? shiftDate(date) : date;
        return dateFormat(shifted, "yyyy-mm-dd HH:MM:ss", true)
    };
    //formatDate(new Date(shifted_to).add({days:1, seconds:-1}));
    $scope.changeDate = function() {
        /*
        $scope.params.from = formatDate($scope.dateRange.from, true);
        $scope.params.to   = formatDate(new Date(shiftDate($scope.dateRange.to)).add({days:1, seconds:-1}), false);
        */
        $scope.params.from = null;
        $scope.params.to   = null;
    };

    // keep reference for the current scope
    
    //COMMON VARS
    $scope.setDateRange = function(range) {
        FilterService.setDateRange(range);
        //$scope.params.date = FilterService.getDateRange();
    };
    var syncDateRangeButtons = function() {
        $scope.dateRangeButtons = FilterService.getDateRangeButtons();
        $scope.currentDate = FilterService.getSelectedDateRangeName();
        $scope.dateRange = FilterService.getDateRange();
        $scope.changeDate();
    };

    syncDateRangeButtons();

    $scope.$on(FilterService.DATE_RANGE_CHANGED, function() {
        //console.log(FilterService.getDateRange());
        $scope.dateRange   = FilterService.getDateRange();
        $scope.currentDate = FilterService.getSelectedDateRangeName();
        $scope.changeDate();
    });



    $scope.select_item = function(el) {
        if ($scope.selected.length > 0 ) {
            var idx = _.indexOf($scope.selected, _.find($scope.selected, function(el2) { return el2.id === el.id } ));
            if (idx != -1) {
                $scope.selected.splice(idx, 1);
            } else {
                $scope.selected.push(el);
            }
        } else {
            $scope.selected.push(el);
        }

    };

    $scope.master = false;
    $scope.select_all = function(all) {
        if (all) {
            for (var i = 0, len = $scope.results.length; i < len; ++i) {
                $scope.selected.push($scope.results[i]);
            }

        } else {
            $scope.selected = [];
        }
    };

    $scope.$watch('master', function(nVal, oVal) {
        if(nVal != oVal) {
            if (nVal == true) {
                $scope.select_all(true);
            } else {
                $scope.select_all(false);
            }
        }
    })

    $scope.$watch('results.length', function(nVal, oVal) {
        if(nVal != oVal || nVal == 0) {
            $scope.master = false;
        }
    })

    $scope.resetVisibilityFilters = function() {
        var params = $scope.params.visibility;
        angular.forEach(params, function(value, key){
            params[key] = false;
        });
        return params;
    };

    $scope.responseType = AppState.read("response_type") || 'pending';
    $scope.responseHeaders = {
            pending : 'pending',
            starred : 'starred',
           rejected : 'rejected',
          forwarded : 'forwarded',
             posted : 'replied',
          retweeted : 'retweeted',
           filtered : 'filtered',
           skipped  : 'skipped',
           review   : 'review'
    };

    // response buttons visibility settings
    $scope.buttonShow = {
           star : true,
        retweet : true,
           skip : true,
         reject : true,
            all : true,
           post : true
    };

    $scope.setButtonsShow = function(show) {
        _.each( $scope.buttonShow, function(val, key) {
                $scope.buttonShow[key] = show;
        } )
    };

    $scope.showAllBtn = function(show) {
        if ($scope.responseType == 'pending' ||
                $scope.responseType == 'filtered' ||
                $scope.responseType == 'skipped') {
            return show
        } else {
            return false;
        }
    };

    $scope.$watch('responseType', function() {
        $scope.results = [];
        $scope.$emit("response_type_changed");
        $scope.fetchResults($scope.responseType);
        switch ($scope.responseType)
        {
            case 'rejected':
                $scope.responseIcon = 'trash';
                $scope.setButtonsShow(false);
                $scope.buttonShow.star = true;
                $scope.buttonShow.retweet = true;
                $scope.buttonShow.skip = true;
                $scope.buttonShow.post = true;
                break;
            case 'posted':
                $scope.responseIcon = 'comment';
                $scope.setButtonsShow(false);
                $scope.buttonShow.retweet = true;
                $scope.buttonShow.star = true;
                break;
            case 'retweeted':
                $scope.responseIcon = 'retweet';
                $scope.setButtonsShow(false);
                $scope.buttonShow.post = true;
                $scope.buttonShow.star = true;
                break;
            case 'skipped':
                $scope.responseIcon = 'step-forward';
                $scope.setButtonsShow(true);
                $scope.buttonShow.skip = false;
                break;
            case 'filtered':
                $scope.responseIcon = 'filter';
                $scope.setButtonsShow(true);
                break;
            case 'review':
                $scope.responseIcon = 'eye-open';
                $scope.setButtonsShow(true);
                break;
            default:
                $scope.responseIcon = 'refresh';
                $scope.setButtonsShow(true);

        }

    });

    $scope.shouldShowReview = function(channel) {
        channel = channel || $scope.channel;
        if (channel) {
            return channel.user_in_review_team;
        } else {
            return _.any($scope.channels, function(item) {
               return item.user_in_review_team;
            });
        }
    };

    $scope.fetchResults = function(type) {
        $scope.responseType = type;
        var params = $scope.resetVisibilityFilters();
        params[type] = true;

    };

    $scope.showStarred = function() {
        var starred = $scope.params.visibility.starred;
        if (starred == false) {
            $scope.params.visibility.starred = true;
            return true;
        } else {
            $scope.params.visibility.starred = false;
            return false;
        }
    };

    //build intentions filter

    $scope.facets = {
        intentions : { visible : false, all : true },
        message_types : { visible : false, all : true },
        statuses : { visible : true, all : false }
    };

    $scope.toggleFacet = function(facetName) {
        var facet = $scope.facets[facetName];
        return facet.visible ? facet.visible = false : facet.visible = true;
    };

	var statusFilters = [
			            { label : 'actionable', display : 'actionable', enabled : true},
			            { label : 'potential' , display : 'potential',  enabled : true},
			            { label : 'rejected'  , display : 'rejected',   enabled : false}
			        ];
	FilterService.getPostStatuses = function() {
		return statusFilters;
	};

    //$scope.intentions_filter = prep_intentions(AppState.read("engage_params"));
    // Set custom status filter for inbox;
    $scope.statuses_filter = FilterService.getPostStatuses();
    FilterService.setIsAllStatuses(false);
    $scope.params.statuses = FilterService.getPostStatusesParams();
    // End set custom status filter for inbox;
    $scope.intentions_filter = FilterService.getIntentions();
    $scope.message_types_filter = FilterService.getMessageTypes();
    $scope.updateIntentions = function() {
        FilterService.updateIntentions();
    };
    
    $scope.updateMessageTypes = function() {
        FilterService.updateMessageTypes();
    };
       
    $scope.updatePostStatuses = function() {
    	FilterService.updatePostStatuses();
    };
    $scope.$watch('facets.intentions.all', function(newVal) {
        FilterService.setIsAllIntentions(newVal);
        if (newVal) {
            FilterService.setIntentions([]);
        }
    });
    $scope.$watch('facets.message_types.all', function(newVal) {
		FilterService.setIsAllMessageTypes(newVal);
		if (newVal) {
			FilterService.setMessageTypes([]);
		}    	
    });
    $scope.$watch('facets.statuses.all', function(newVal) {
        FilterService.setIsAllStatuses(newVal);
        if (newVal) {
            FilterService.setStatuses([]);
        }
    });

    var updateMessageTypes = function() {
        var selected = FilterService.getSelectedMessageTypes();
        if (selected.length > 0 ) {
            FilterService.setIsAllMessageTypes(false);
            $scope.facets.message_types.all = false;
        } else {
            $scope.facets.message_types.all = true;
        }
        $scope.params.message_type = FilterService.getMessageTypesParams();
    }

    $scope.$on(FilterService.MESSAGE_TYPE_CHANGED, function() {
        updateMessageTypes();
    });
    $scope.message_type = {
        selected : null
    }
    $scope.$watch('message_type.selected', function(nVal) {
        if (nVal) {
            console.log(nVal);
            $scope.params.message_type = [nVal.label]
        } else {
            $scope.params.message_type = [0,1]
        }
    })

    $scope.$on(FilterService.INTENTIONS_CHANGED, function() {
        var selected = FilterService.getSelectedIntentions();
        if (selected.length > 0 ) {
            FilterService.setIsAllIntentions(false);
            $scope.selectedIntentions = selected;
            $scope.facets.intentions.all = false;
        } else {
            $scope.selectedIntentions = [];
            $scope.facets.intentions.all = true;
        }
        $scope.params.intentions = FilterService.getIntentionsParams();
    });
    
    $scope.$on(FilterService.POST_STATUSES_CHANGED, function() {
        var selected = FilterService.getSelectedPostStatuses(true);
        if (selected.length > 0 ) {
            FilterService.setIsAllStatuses(false);
            $scope.selectedStatuses = selected;
            $scope.facets.statuses.all = false;
        } else {
            $scope.selectedStatuses = [];
            $scope.facets.statuses.all = true;
        }
        $scope.params.statuses = FilterService.getPostStatusesParams();
    });

    // watch params changed and trigger fetching filtered results from the server
    $scope.$watch( 'params', function(newVal, oldVal) {
        if (newVal !== oldVal) {
            $scope.$emit("params_changed");
            $scope.loadResponses();
        }
    }, true);

    
    $scope.$watch( 'delta_responses', function(newVal, oldVal) {
        if(newVal != -1) {
            $scope.loadResponses();
        }
    });
    
    $scope.skipCreativePredicate = function(post) {
        var creative = post.match.matchable.creative.toLowerCase() +
                post.post.text;
        var skips = $scope.params.skip_creative;

        return _.all(skips, function(term){
            return (creative.indexOf(term.toLowerCase()) == -1)
        });
    };

    //services classes for ACTIONS - here we set REST endpoints
    var Responses = $resource('/responses/json', {}, {
    //var Responses = $resource('/static/assets/js/json/responses.json?aaa', {}, {
        fetch: {method:'POST' , isArray:false}
        //fetch: {method:'GET' , isArray:false}
    });


    var UserProfile = $resource('/user_profile/json', {}, {
        fetch: {method:'GET' , isArray:false}
    });

    $scope.responseCommand = Response;

    var Matchable = $resource('/matchables/json', {}, {
       next: {method:'GET', params: {response : "@id"}, isArray:false}
    });

    /***** ACTIONS *****/
    $scope.results = [];

    //fetch all responses
    $scope.default_profile_url = "/static/assets/img/default_profile2.png";
    $scope.loadResponses = function() {
        var params = _.extend({}, $scope.params);
        params['delta_responses'] = $scope.delta_responses;
        if ($scope.channel != null) {
            //console.log("load responses");
            var loader = jQuery("#loader");
            var backdrop = jQuery("#loader-backdrop");

            loader.show();
            backdrop.show();
            
            Responses.fetch(params, function(res) {
                $scope.acc = AccountsService.getCurrent();
                if ($scope.delta_responses != -1) {
                    angular.forEach(res.list, function(el) {
                        $scope.results.push(el);
                    });
                    $scope.delta_responses = -1
                } else {
                    $scope.results = [];
                    $scope.results = res.list;
                }
                loader.hide();
                backdrop.hide();
                $scope.$emit('ON_RESPONSES_LOADED');
            });
        }
    };

    var loadSmartTags = function(channel_id) {
        SmartTags.fetch(channel_id).then(function(d) {
            $scope.smart_tags = d;
            if ($scope.smart_tag.selected != null) {
                var selected = _.indexOf(_.pluck(d, 'id'), $scope.smart_tag.selected.id);
                $scope.smart_tag.selected = $scope.smart_tags[selected];
            }
        });
    };

    $scope.$on('channel_selected', function(evnt) {
        var channel = evnt.targetScope.channel;
        loadSmartTags(channel.id);
    });
    $scope.$on(SmartTag.ON_SMARTTAG_UPDATE, function(){
        console.log("I hear you!");
        var channel = $scope.channel;
        loadSmartTags(channel.id);
    });
    $scope.$watch('smart_tag.selected', function(nVal, oVal) {
        if (nVal !== oVal) {
            $scope.params.channel_id = nVal ? nVal.id : $scope.channel.id;
        }
    });

    $scope.$on(SmartTags.ON_POST_TAGS_REMOVED, function(event, response_id, post_id, tag_removed, is_conv) {
        //console.log("We are in inbox = Remove response!");
        if (is_conv) {
           event.preventDefault()
        }
        var removed_tag = tag_removed || event.targetScope.tag;
        if ($scope.smart_tag.selected && $scope.smart_tag.selected.id == removed_tag.id) {
            $scope.removeResponse(response_id);
        }
    });



    // star / unstar response
    $scope.markResponse = function( el ) {
        if (el != null) {
            if (!el.starred)  {
                $scope.starItems([el]);
            } else {
                $scope.unStarItems([el]);
            }
        } else {
            //group starring
            if( $scope.selected.length > 0 ) {
                $scope.unStarItems($scope.starred);
                $scope.starItems($scope.unstarred);
            } else {
                SystemAlert.error("Please select any item to star");
            }
        }
    };

    $scope.starItems = function(items) {
        $scope.responseCommand.star({"responses" :_.pluck(items, 'id'), 'tag' : $scope.getChannelId()}, function(res) {
            angular.forEach(items, function(el) {
                el.starred = true;
                el.starClass = "btn-success";

            });
            items = [];
        });
    };

    $scope.unStarItems = function(items) {
        $scope.responseCommand.unstar({"responses" : _.pluck(items, 'id'), 'tag' : $scope.getChannelId()}, function(res) {
            angular.forEach(items, function(el) {
                el.starred = false;
                el.starClass = "";
            });
            items = [];
        });
    };

    $scope.$watch('selected', function(newVal, oldVal) {
        if (newVal !== oldVal) {
            $scope.starred = [];
            $scope.unstarred = [];
            angular.forEach($scope.selected, function(item) {
                // get local scope
                if (item.starred == true) {
                    $scope.starred.push(item);
                } else {
                    $scope.unstarred.push(item);
                }

            });
            //console.log($scope.starred);
        }
    }, true);


    $scope.removeResponseOld = function( el ) {
        for (var i = 0, len = $scope.results.length; i < len; ++i) {
            if (_.isArray(el)) {
                for (var j = 0, lenj = el.length; j < lenj; ++j) {
                    if (el[j] === $scope.results[i]) {
                        $scope.results.splice(i, 1);
                    }
                }
            } else {
                var res_id = $scope.results[i]['id'];
                if (el == res_id) {
                    $scope.results.splice(i, 1);
                    return;
                }
            }
        }
    };

    $scope.removeResponse = function( el, sc ) {
        if (_.isArray(el) ) {
           $scope.results = _.difference($scope.results, el);
           if ($scope.params.visibility.pending) {
           		// If we are in the pending section of the inbox, load
           		// more respones to keep the queue going
            	//$scope.loadResponses(el.length);
               $scope.delta_responses = el.length;
            }
        } else {
            var idx = -1;
            if (_.isObject(el)) {
                idx = _.indexOf($scope.results, el);
            } else {
                idx = _.indexOf($scope.results, _.find($scope.results, function(i) { return i.id === el }));
            }
            if (idx !== -1) {
                  $scope.results.splice(idx, 1);
                  if ($scope.params.visibility.pending) {
                	// If we are in the pending section of the inbox, load
           			// more respones to keep the queue going
                      $scope.delta_responses = 1;
                  }	
            }
        }
    };

    // reject response
    $scope.rejectResponse = function( el ) {
        //pass the item scope from ng-repeat
        var itemScope = this;
        if (el != null) {
            $scope.responseCommand.reject({"responses" : [el.id], 'tag' : $scope.getChannelId()}, function(res) {
                $scope.removeResponse(el, itemScope);
                //$scope.loadResponses();
            });
        } else {
            if ($scope.selected.length > 0) {
                $scope.responseCommand.reject({"responses" :_.pluck($scope.selected,'id'), 'tag' : $scope.getChannelId()}, function(res) {
                    $scope.removeResponse($scope.selected);
                    $scope.selected.length = 0;
                    //$scope.loadResponses();
                });
            } else {
                SystemAlert.info("Please select the items to reject");
            }
        }
    };

    // retweet response
    $scope.retweetResponse = function( el ) {
        //pass the item scope from ng-repeat
        var itemScope = this;
        $scope.responseCommand.retweet({"response" : el.id, 'tag' : $scope.getChannelId()}, function(res) {
                $scope.removeResponse(el, itemScope);
                if (res.item && res.item.status == 'review-retweet') {
                    toaster.pop('info', 'Response is placed for review prior to dispatch');
                }
        }, function onError(res) {
            if (res.error_code == 1) {
                $scope.loadResponses();
            }
        });
    };
    
    // retweet response
    $scope.followUser = function( el ) {
        //pass the item scope from ng-repeat
        var itemScope = this;
        $scope.responseCommand.follow({"response" : el.id, 'tag' : $scope.getChannelId()}, function(res) {
            el.is_followed = true;
        });
    };
    
    
    // retweet response
    $scope.unfollowUser = function( el ) {
        //pass the item scope from ng-repeat
        var itemScope = this;
        $scope.responseCommand.unfollow({"response" : el.id, 'tag' : $scope.getChannelId()}, function(res) {
            el.is_followed = false;
        });
    };
    
    // retweet response
    $scope.likeResponse = function( el ) {
        //pass the item scope from ng-repeat
        var itemScope = this;
        $scope.responseCommand.like({"response" : el.id, 'tag' : $scope.getChannelId()}, function(res) {
            if (el.post.liked) {
                el.post.liked = false;
            } else {
                el.post.liked = true;
            }
        });
    };
    
    // retweet response
    // $scope.shareResponse = function( el ) {
        // //pass the item scope from ng-repeat
        // var itemScope = this;
        // $scope.responseCommand.share({"response" : el.id, 'tag' : $scope.getChannelId()}, function(res) {
        // });
    // };

    // skip response
    $scope.skipResponse = function( el ) {
        //pass the item scope from ng-repeat
        var itemScope = this;
        //console.log(itemScope);
        //console.log($scope.selected);
        if (el != null) {
            $scope.responseCommand.skip({"responses" : [el.id], 'tag' : $scope.getChannelId()}, function() {
                $scope.removeResponse(el, itemScope);
            });
        } else {
            if ($scope.selected.length > 0) {
                $scope.responseCommand.skip({"responses" : _.pluck($scope.selected,'id'), 'tag' : $scope.getChannelId()}, function(res) {
                    $scope.removeResponse($scope.selected);
                    $scope.selected.length = 0;
                });
            } else {
                SystemAlert.info("Please select the items to skip");
            }
        }
    };



    var getMatchable = function(el) {
        if (el.matchable) {
            return el.matchable;
        } else {
            return el.item ? el.item.match.matchable : el.match.matchable;
        }
    };
    var getResponse = function(el) {
        if (el.item) {
            return el.item
        } else if(el.match) {
            return el
        } else {
            // in matches dialog
            return $scope.dialogScope.response;
        }
    };

    // post response
    $scope.postResponse = function( el, id, type ) {
        //pass the item scope from ng-repeat
        // type will be public or direct depending on what action we took
        var itemScope = this;
        var match_id = el.match ? el.match.matchable.id : el.matchable.id;
        var response_id = id ? id : el.id;
        var resp = getResponse(el);
        var params = {
                "matchable" : match_id,
                "response"  : response_id,
                "prefix"    : resp ? resp.prefix : '',
                "suffix"    : resp ? resp.suffix : '',
                "latest_post" : resp ? resp.post.id_str : '',
                "message_type" : type ? type : 'direct',
                "tag" : $scope.getChannelId()
            };
        $scope.responseCommand.post(params,
            function(res) {
                console.log("OK!");
                $('#matchableModal').modal('hide');
                $scope.removeResponse(getResponse(el).id);
                if (res.item && res.item.status == 'review-post') {
                    toaster.pop('info', 'Response is placed for review prior to dispatch');
                }
            }, function onError(res) {
                if (res.error_code == 1) {
                    $scope.loadResponses();
                }
            }
        );
    };

    // post and create SFDC case
    $scope.postResponseCreateCase = function( el, id ) {
        //pass the item scope from ng-repeat
        var itemScope = this;
        var match_id = el.match ? el.match.matchable.id : el.matchable.id;
        var response_id = id ? id : el.id;

        $scope.responseCommand.post_response_and_case(
            {
                "matchable" : match_id,
                "response"  : response_id,
                "latest_post" : getResponse(el).post.id_str,
                "tag"       : $scope.getChannelId()

            },
            function(res) {

                    $('#matchableModal').modal('hide');
                    $scope.removeResponse(getResponse(el).id);
                    if (res.item && res.item.status == 'review-post') {
                        toaster.pop('info', 'Response is placed for review prior to dispatch');
                    }

            }, function onError(res) {
                if (res.error_code == 1) {
                    $scope.loadResponses();
                }
            }
        );
    };

    // post and create SFDC case
    $scope.postCustomResponseCreateCase = function( el ) {
        console.log(el);
        var original_creative = getMatchable(el).creative;
        var custom_creative = el.custom_response;

        if (original_creative != custom_creative) {
            $scope.responseCommand.post_custom_response_and_case(
                {
                    "creative": el.custom_response,
                    "response" : getResponse(el).id,
                    "latest_post" : getResponse(el).post.id_str,
                    "tag"    : $scope.getChannelId()
                },
                function(res) {
                    $scope.removeResponse(getResponse(el).id);
                    $('#matchableModal').modal('hide');
                    if (res.item && res.item.status == 'review-post') {
                        toaster.pop('info', 'Response is placed for review prior to dispatch');
                    }
                }
            );
        } else {
            SystemAlert.info("Please make changes to the content to be able to submit custom response");
        }
    };



    $scope.startEdit = function(el) {
    	if ($scope.responseType != 'posted') {
    		el.custom_response = getMatchable(el).creative;
       		el.isEditMode = true;
    	} else {
    		return false;
    	}
    };

    $scope.cancelEdit = function(el) {
        el.isEditMode = false;
    };

    $scope.submitCustomResponse = function(el, message_type) {

        console.log(el);
        var original_creative = getMatchable(el).creative;
        var custom_creative = el.custom_response;

        console.log(original_creative);
        console.log(custom_creative);

        //make sure they are different
        if (original_creative != custom_creative) {
            $scope.responseCommand.post_custom(
                { "creative": el.custom_response,
                  "response" : getResponse(el).id,
                  "prefix" : getResponse(el).prefix,
                  "suffix" : getResponse(el).suffix,
                  "latest_post" : getResponse(el).post.id_str,
                  "tag"    : $scope.getChannelId(),
                  "message_type" : message_type
                },
                function(res) {

                    $scope.removeResponse(getResponse(el).id);

                    $('#matchableModal').modal('hide');
                    if (res.item && res.item.status == 'review-post') {
                        toaster.pop('info', 'Response is placed for review prior to dispatch');
                    }
                }, function onError(res) {
                    if (res.error_code == 1) {
                        $scope.loadResponses();
                    }
                }
            );
        } else {
            SystemAlert.info("Please make changes to the content to be able to submit custom response");
        }

    };

    $scope.nexMatch = function( el ) {

          var response = el.item,
                   ids = response.other_matches,
             matchable = response.match.matchable;

        //we will cycle through the available matchables
        if (el.count < (ids.length-1)  ) {
            el.count++;
        } else {
            el.count = 0;
        }

        //fetch the next match (matchable)
        var pl = Matchable.next({ "id" : ids[el.count], "response" : response.id} , function() {

                   matchable.stats.ctr = pl.item.stats.ctr;
           matchable.stats.impressions = pl.item.stats.impressions;
             matchable.stats.relevance = pl.item.stats.relevance;
                    matchable.creative = pl.item.creative;

        });

        //console.log(el.item.other_matches[el.count]);
    };

    $scope.allMatchables = [];

    /* post model for all matches' modal window */
    $scope.post = {
        profile_image_url: "",
                     name: "",
              screen_name: "",
                     text: "",
                 creative: ""
    };

    $scope.limitOptions = [5, 10, 20, 50];
    $scope.limit = 10;
    $scope.searchTerm = "";
    $scope.replyChannel = "";
    $scope.replyContent = "";
    
    $scope.openMatchesDialog = function( response ) {

        var post = response.post,
            match = response.match;

        $scope.dialogScope = {
            response : response,
            post     : post,
            match    : match,
            acc      : AccountsService.getCurrent()
        }

        $scope.fetchMatchables(function(){
            // show modal with all the matchables and the current post
            $('#matchableModal').modal('show');
        });
    }

	$scope.allMatchesShowPost = function(item) {
		return $scope.dialogScope.response.has_both_pub_and_dm || item.message_type == 0;
	}

    $scope.caseButtonVisibility = function(item) {
        return !item.is_conversation_synced && $scope.buttonShow.post && $scope.acc.is_sf_auth;
    }

    $scope.fetchMatchables = function(callback) {
        var response = $scope.dialogScope.response,
                post = $scope.dialogScope.post,
                matchable = $scope.dialogScope.match ? $scope.dialogScope.match.matchable : $scope.dialogScope.matchable;

        var params = {
            "response": response.id,
            "search_term": $scope.searchTerm,
            "limit": $scope.limit
        }

        Matchable.next(params, function(res) {
                // update post
                $scope.post = {
                    profile_image_url : post.user.profile_image_url,
                    name              : post.user.name,
                    screen_name       : post.user.screen_name,
                    text              : $sce.trustAsHtml(post.text),
                    created_at        : post.created_at,
                    message_type      : post.message_type,
                    creative          : matchable.creative,
                    response_id       : response.id
                };

                $scope.allMatchables = _.map(res.list, function(item) {
                    item.isEditMode = false;
                    return {
                        matchable : item,
                        post      : post,
                        id        : response.id,
           is_conversation_synced : response.is_conversation_synced,
                     message_type : response.message_type
                    };
                });

                if (callback) callback();
        } );
    };

    $scope.sortBy = function(what) {

        $scope.params.sort_by = what;
        //$scope.loadResponses();

    };

    $scope.reloadBatch = function() {
        $scope.loadResponses();
    };

    $scope.visitUserProfile = function(post) {
        var user = post.user.screen_name;
        var profile_url = post.user.profile_url;

        if (user && user !== 'anonymous') {
            //$window.location.href=profileBase + user;
            $window.open(profile_url)
        } else {
            SystemAlert.error("There is no profile for the user");
        }

    };

    $scope.user_profile = {};
    $scope.user_profile.posts = [];

    $scope.getUserProfile = function(post) {
        $scope.user_profile.posts = [];
        $scope.user_profile.user = post.user.screen_name;
        UserProfile.fetch(
                {
                    channel_id : ChannelsService.getSelectedId(),
                    user_name : $scope.user_profile.user
                }, function(res) {
                    $scope.user_profile.posts = res.list;
                });
        $('#userProfileModal').modal('show');
    };

    $('.responseText a').on('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        $window.open(e.target.href);
    });

    $("body").on("mouseover", "table.response .actions",
            function() {
                $(this).find(".btn").removeClass("disabled");
            });

    $("body").on("mouseleave", "table.response .actions",
            function() {
                $(this).find(".btn").addClass("disabled");
            });
}

