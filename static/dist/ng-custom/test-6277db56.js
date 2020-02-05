angular.module('test', ['ui.select2', 'ui.jq', 'ngResource', 'ngSanitize', 'slr.components']);

angular.module('test')
    .controller('TestCtrl', ["$log", "$scope", "$resource", "$http", "SystemAlert", function($log, $scope, $resource, $http, SystemAlert) {

    /* Channels Selector */
    $scope.channels = [];
    $scope.channel = null;
    $scope.channel_id = undefined;
    $scope.post = '';
    $scope.message_type = false;
    $scope.submittedPost = {};
    $scope.user_tag = '';
    $scope.channelReset = false;
    $scope.channelMatching = false;

    var Channels = {};
    Channels.load = function() {
       var promise = $http({
            method : 'POST',
            url    : '/channels_by_type/json',
            data : {
                type          : ['inbound', 'outbound'],
                serviced_only : false,
                parent_names  : true }
       }).then(function (res) {
          return _.filter(res.data.list, function(el) {
              return el.parent_id == null && el.is_compound == false ||
                     el.parent_id != null && el.type == 'inbound' })
       });
       return promise;
    };

    Channels.load().then(function(channels) {
        $scope.channels = channels;
        $scope.channel =  channels[0];
    });

    $scope.$watch('channel', function(newVal, oldVal) {
        //console.log($scope.channel);
        if (newVal != oldVal) {
            $scope.channel_id = $scope.channel ? $scope.channel.id : null;
            $scope.channelClassifier = false;
        } else {
            $scope.channel_id = null;
        }
    });


    angular.element('textarea').keypress(function(event) {
        // Check the keyCode and if the user pressed Enter (code = 13)
        // disable it

        if (event.keyCode == 13) {
            event.preventDefault();
            $scope.submitPost();
        }
    });


//services classes for ACTIONS - here we set REST endpoints
    var TestPost = $resource('/commands/create_post', {}, {
        submit: { method:'POST' , isArray:false}
    });

    var Classifier = $resource('/test/classifier',{},{
        classifier : {method: 'POST' , isArray:false}
    });

    var Matching = $resource('/test/matcher',{},{
        matcher : {method: 'POST' , isArray:false}
    })

    var PurgeTopics = $resource('/test/purge_topics',{},{
        purger : {method: 'POST' , isArray:false}
    })

    $scope.refreshChannelReset = function(){
        $scope.channelClassifier = false;
    }

    $scope.refreshMatcherReset = function(){
        $scope.channelMatching = false;
    }

    $scope.reset = function() {
        
        var res = Classifier.classifier({},{
            "channel": $scope.channel_id,
            "action" : "reset"
        }, function() {
            $scope.ClassifierResult = "Classifier has been Reset. The process took " + res.elapsed_time + " seconds."
                                      + " " + res.message;
            $scope.channelClassifier = true;
        })
    }

    $scope.resetMatching = function() {

        var res = Matching.matcher({},{
            "channel": $scope.channel_id,
            "action" : "reset"
        }, function() {
            $scope.MatchingResult = "Matching has been Reset. The process took " + (res.elapsed_time) + " seconds."
                                    + " " + res.message;
            $scope.channelMatching = true;
        })
    }

    $scope.retrain = function() {
        
        var res = Classifier.classifier({},{
            "channel": $scope.channel_id,
            "action" : "retrain"
        }, function() {
            $scope.ClassifierResult = "Classifier has been Retrained. The process took " + res.elapsed_time.toString() + " seconds"
            $scope.channelClassifier = true;
        })
    }
    $scope.printScope = function(sa) {
        console.log(sa);
    }
    $scope.submitPost = function() {
        var post = $scope.post;
        if (post.replace(/\s/g, "") != '') {
            var res = TestPost.submit({}, {
                "channel" : $scope.channel_id,
                "content" : $scope.post,
                "user_tag" : $scope.user_tag,
                "message_type" : $scope.message_type
            }, function() {
                $scope.submittedPost = res.item;
                $scope.featureVector = $scope.submittedPost.feature_vector.sort();
            })
        } else {
            SystemAlert.info("Please enter the post content");
            $scope.post = "";
        }
    }


}]);