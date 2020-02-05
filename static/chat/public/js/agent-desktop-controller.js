'use strict';

angular.module('chat')
  .controller('AgentDesktopCtrl',
      function ($scope,
                $rootScope,
                $window,
                $stateParams,
                $state,
                $http,
                $modal,
                socket,
                useragent,
                geolocation,
                AuthService,
                AgentService,
                ChannelsService,
                ChatSummaryService,
                EventsService,
                SessionsService) {

    $scope.agentId = window.agentId;
    $scope.agent = {};

    $scope.customers = [];
    $scope.selectedCustomer = null;
    $scope.messages = [];
    $scope.user = {}; //holds information about the current user
    $scope.rooms = []; //holds information about all rooms
    $scope.error = {};
    $scope.joined = false;
    $scope.isExpanded = false;
    $scope.currentSubTab = '';
    $scope.viewDispositionTab = false;

    $scope.sessionId = null;

    $scope.channel_id = null;
    $scope.summary    = {};

    var typing = false;
    var timeout  = undefined;
    var userNames = {
      0: 'Me',
      1: 'Customer',
      2: 'ChatBot',
      3: 'Supervisor'
    };

    $scope.showModal = false;
    $rootScope.chatArticleType = '';
    $scope.toggleModal = function(type){
        $scope.showModal = !$scope.showModal;
        $rootScope.chatArticleType = type;
    };

    /* ABOUT PAGE */
    $scope.about = function() {
        var modalInstance = $modal.open({
            templateUrl: 'aboutModal',
            controller: aboutModalCtrl
        });
    };

    var aboutModalCtrl = function($scope, $modalInstance) {
        $scope.cancel = function() {
            $modalInstance.dismiss('cancel');
        };
    };
    /* ABOUT PAGE END */

    $scope.toggleChatbox = function() {
        $scope.isExpanded = !$scope.isExpanded;
    };

    $scope.toggleChatboxToExpand = function() {
        $scope.isExpanded = true;
    };

    $scope.selectCustomer = function(customer) {
        $scope.selectedCustomer = customer;
        customer.isUnread = false;

        $scope.currentSubTab = customer.userID + '-summary';
    };

    $scope.selectSubTab = function(tab) {
        $scope.currentSubTab = $scope.selectedCustomer.userID + '-' + tab;
    };

    $scope.removeCustomer = function(customer) {
        var index = $scope.customers.indexOf(customer);
        $scope.customers.splice(index, 1);
    };

    function processMessage(data) {
        var message = {
            sender  : userNames[data.senderType],
            from    : data.from,
            body    : data.message
        };

        var customer = $scope.selectedCustomer;

        if (!customer) {
            return;
        }

        if (data.senderType === 2 && customer.userID != message.from || message.sender==="ChatBot") {    // Chat bot for logs
            console.log("PUSH LOGS MESSAGES", message);
            customer.logs.push(message);
        } else {
            console.log("PUSH CUSTOMER MESSAGES", message);
            customer.isUnread = true;
            customer.messages.push(message);
        }
    }

    $scope.focus = function(bool) {
        $scope.focussed = bool;
    };

    $scope.typing = function(event, user, customer) {
        function timeoutFunction() {
            typing = false;
            if (!$scope.selectedCustomer) {
                return;
            }
            socket.emit('typing', {
                senderType: 0,
                isTyping: false,
                from: $scope.agentId,
                toRoom: user.inroom
            });
        }

        if (event.which !== 13) {
            if (typing === false && $scope.focussed && user.inroom !== null) {
                typing = true;
                socket.emit('typing', {
                    senderType: 0,
                    isTyping: true,
                    from: $scope.agentId,
                    toRoom: user.inroom
                });
                clearTimeout(timeout);
                timeout = setTimeout(timeoutFunction, 500);
            }
        }
    };

    socket.on('isTyping', function(data) {
        if (data.from != $scope.agentId) {
            $scope.selectedCustomer.typer = userNames[data.senderType];
            $scope.selectedCustomer.isTyping = data.isTyping;
        }
    });

    $scope.token = null;
    $scope.joinServer = function() {
        //console.log("EMIT JOIN ON SOCKET!");

        AuthService.authenticate({
            username: 'super_user@solariat.com',
            password: 'password'
        })
            .then(function(response) {

                $scope.token = response.data.token;
                return AgentService.getById($scope.token, $scope.agentId);
            })

            .then(function(response) {


                $scope.agent = angular.copy(response.data.item);

                socket.emit('joinSocketServer', {
                    userID: $scope.agent.id,
                    userType: 'agent',
                    userName: $scope.agent.agent_full_name
                });
                $scope.joined = true;
                $scope.error.join = '';
                //console.log("JOINED? " + $scope.joined);

                //get right channel
                ChannelsService.getByPlatform($scope.token, 'chat')
                  .then(function(channels) {

                    $scope.channel_id = channels.data.list[0].id;

                    var apiUrl = ("http://{{HOST_DOMAIN}}/api/v2.0/events/tags").replace("{{HOST_DOMAIN}}", HOST_DOMAIN);
                    $http.get(apiUrl, {
                      params : {
                        token      : $scope.token,
                        channel_id : $scope.channel_id
                      }
                    }).success(function(data) {
                      console.log("GET TAGS", data);
                      $scope.temp_tags = data.list;
                    })
                  })
            });
    };



/* ----- -*/

        $scope.person = {};



        $scope.tagTransform = function (newTag) {
          var item = {
            name: newTag,
            email: newTag.toLowerCase()+'@email.com',
            age: 'unknown',
            country: 'unknown'
          };

          return item;
        };
        /* ----- -*/



    $scope.$watch('summary.last_event_id', function(nVal, oVal) {
      if(nVal) {
        $scope.tags = $scope.temp_tags;
      } else {
        $scope.tags = []
      }
    })

     $scope.acceptTag = function(item, model) {
          var apiUrl = ("http://{{HOST_DOMAIN}}/api/v2.0/events/accept").replace("{{HOST_DOMAIN}}", HOST_DOMAIN);
         $http.post(apiUrl, {
           token: $scope.token,
           tag_id: item.id,
           event_id: $scope.summary.last_event_id
         })
     }

        $scope.removeTag = function(item, model) {
          var apiUrl = ("http://{{HOST_DOMAIN}}/api/v2.0/events/reject").replace("{{HOST_DOMAIN}}", HOST_DOMAIN);
          $http.post(apiUrl, {
            token: $scope.token,
            tag_id: item.id,
            event_id: $scope.summary.last_event_id
          })
        }

    $scope.setChatSummary = function(resp) {
      console.log("setChatSummary", resp);
      var data = resp.data ? resp.data : resp;
      console.log("NOTIFY SU ON SUMMARY FETCH", resp);
      socket.emit('notifySupervisor', {
        summary: data.item.summary,
        agent: $scope.agent
      });
      $scope.summary.last_event_id = data.item.summary.latest_event_id;
      $scope.summary.tags   = data.item.summary.tags;
      $scope.summary.topics = data.item.summary.topics;
      $scope.summary.sentiment_score = data.item.summary.sentiment_score;
      console.log("SUMMARY SHOW", $scope.summary);
    };

    $scope.supervisorAlertId = null;
    $scope.doNothingAlertId = null;

    $scope.nextBestActionChat = function(data) {
      var eventData = data.data.item;
      var apiUrl = ('http://{{HOST_DOMAIN}}/api/v2.0/next_best_action/query').replace("{{HOST_DOMAIN}}", HOST_DOMAIN);
      $http.post(apiUrl, {
                  token: $scope.token,
                  event_id: eventData.id,
                  customer_id: eventData.actor_id,
                  event_type: 'chat'
              }).then(function(data) {
              var possibleActions = data.data.list;
              var supervisorAlert = _.filter(possibleActions, function(item) {return item.name == "Alert Supervisor"})[0];
              var doNothingAlert = _.filter(possibleActions, function(item) {return item.name == "Do Nothing"})[0];
              $scope.supervisorAlertId = supervisorAlert.id;
              $scope.doNothingAlertId = doNothingAlert.id;
              if ($scope.supervisorAlertId == data.data.list[0].id) {
                  console.log("SHOULD ALERT SUPERVISOR");
                  $scope.askToSupervisor($scope.selectedCustomer, 0);
              } else {
                  console.log("SHOULD JUST CHILL AND RELAX");
              }
              console.log("Chat message next best actions:", data);
          });
    };

    $scope.send = function(customer) {
        if (typeof this.message === 'undefined' || (typeof this.message === 'string' && this.message.length === 0)) {
            $scope.error.send = 'Please enter a message';
        } else {
            socket.emit('send', {
                senderType: 0,
                from: $scope.agentId,
                message: this.message
            });
            this.message = '';
            this.error.send = '';
        }
    };



    $scope.createRoom = function() {
        socket.emit('createRoom');
        $scope.error.create = '';
        if (!$scope.user.inroom) {
            $scope.messages = [];
            $scope.roomname = '';
        }
    };


    $scope.dispatchChatMessage = function(message) {
        console.log("SendChatMessage --> ", message);
          console.log("Grab new chat session", $scope.sessionId);
          console.log("NOTIFY SU HERE");

          if($scope.token && $scope.channel_id) {
            var userId = message.from;
              if(message.senderType == 0 || message.senderType == 3) {
                console.log("Agent - post to outbound");
                EventsService.postEvent({
                  content   : message.message,
                  channels  : [$scope.channel_id],
                  token     : $scope.token,
                  type      : 'chat',
                  is_inbound: false,
                  session_id: $scope.sessionId,
                  actor_id  : $scope.agentId
                })
                .then(function(data) {
                  console.log("Post by Agent was submitted", data);
                  $scope.setChatSummary(data);
                })
              } else if (message.senderType == 1) {
                console.log("CUSTOMER POSTING A MESSAGE, HIS SESSION ID IS", $scope.sessionId);
              //Customer - post to inbound
                EventsService.postEvent(
                  {
                    content   : message.message,
                    channels  : [$scope.channel_id],
                    token     : $scope.token,
                    type      : 'chat',
                    is_inbound: true,
                    session_id: $scope.sessionId,
                    actor_id  : userId //message.userId
                  })
                  .then(function (data) {
                    console.log("Post by Customer was submitted", data);
                    //return ChatSummaryService.getById($scope.token, data.customer_id)
                    $scope.nextBestActionChat(data);
                    $scope.setChatSummary(data);
                  })
              }
            } //if
    }

    socket.on('updateInitialState', function(event) {
        socket.emit('getSessionId', event.actor_id, function(computedSessionId) {
                console.log("GOT A NEW SESSION ID", computedSessionId);
                $scope.sessionId = computedSessionId;
                var apiUrl = ('http://{{HOST_DOMAIN}}/api/v2.0/chat/join_conversation').replace("{{HOST_DOMAIN}}", HOST_DOMAIN);
                $http.post(apiUrl, {
                      token: $scope.token,
                      session_id: computedSessionId,
                      agent_id: $scope.agentId
                  }).then(function(data) {
                     $scope.setChatSummary({item: event});
                     $scope.nextBestActionChat({data: {item: event}});
                     console.log("AGENT SUCCESSFULLY JOINED SESSION", $scope.agentId, computedSessionId);
                  });
            });

        var messageData = {
            senderType: 1,
            from: event.actor_id,
            message: event.content
        };
        processMessage(messageData);
    });

    socket.on('sendUserDetail', function(data) {
        $scope.user = data;
    });


    socket.on('sendChatMessage', function(message) {
      if (message.senderType == 1 || message.senderType == 0 || message.senderType == 3) {
          if (!$scope.sessionId) {
            socket.emit('getSessionId', $scope.selectedCustomer.userID, function(computedSessionId) {
                console.log("GOT A NEW SESSION ID", computedSessionId);
                $scope.sessionId = computedSessionId;
                $scope.dispatchChatMessage(message);
            });
          } else {
              $scope.dispatchChatMessage(message);
          }
      }
      processMessage(message);
    });


  $scope.$watch('selectedCustomer', function(nVal, oldVal) {
    if(nVal !== null) {

      ChannelsService.getAll($scope.token)
        .then(function(response) {
            var chat_channels = _.filter(response.data.list, function (c) {return c.platform === 'Chat'});
            return SessionsService.getByCustomer($scope.token, nVal.userID, chat_channels[0].id)
        })
        .then(function(response) {
          $scope.sessions = response.data.list;
        })

    }

  })


    $scope.getChatSummary = function(c_id) {

      ChatSummaryService.getById($scope.token, c_id)
        .then(function(resp) {
          $scope.open(resp.data.list);
        })
    }


      $scope.open = function (list) {
          $modal.open({
                  templateUrl: 'myModalContent.html',
                  controller: function($scope) {
              },
              size: ""
          });
      };

      $scope.askToSupervisor = function(customer, isFeedback) {
          if (isFeedback != 0) {
              var apiUrl = ('http://{{HOST_DOMAIN}}/api/v2.0/next_best_action/feedback').replace("{{HOST_DOMAIN}}", HOST_DOMAIN);
              $http.post(apiUrl, {
                    token       : $scope.token,
                    action_id   : $scope.supervisorAlertId,
                    event_id    : $scope.summary.last_event_id,
                    score       : 1,
                    customer_id : $scope.selectedCustomer.userID,
                    event_type  : 'chat'
                }).then(function(response) {
                    if (response.status === 200) {
                        console.log('Successfully sent feedback for next_best_action on chat');
                    }
                });
          }
          socket.emit('askToSupervisor', {'customer': {
                                                          id: customer.userID,
                                                          name: customer.userName
                                                      },
                                          'alert_data': {
                                                           action_id: $scope.supervisorAlertId,
                                                           event_id: $scope.summary.last_event_id,
                                                           customer_id: $scope.selectedCustomer.userID,
                                                           do_nothing_id: $scope.doNothingAlertId
                                                        }
          });
      };

    socket.on('sendChatMessageHistory', function(data) {
        angular.forEach(data, function(message) {
            processMessage(message);
        });
    });

    socket.on('connectingToSocketServer', function(data) {
        //console.log("CONNECTED TO SOCKET!!!");
        $scope.joinServer();
        $scope.status = data.status;
    });

    socket.on('updateUserDetail', function(data) {
        $scope.users = data;
        angular.forEach($scope.customers, function(customer) {
            customer.isConnected = false;
            //customer.isUnread = false;
        });

        angular.forEach(data, function (person) {
            var cId = -1;

            angular.forEach($scope.customers, function(customer, idx) {
                if (customer.userID === person.userID) {
                    cId = idx;
                }
            });

            if (person.userType == 'customer' && person.inroom) {
                if (cId === -1) {
                    cId = $scope.customers.length;
                    $scope.customers.push(person);
                    $scope.customers[cId].messages = [];
                    $scope.customers[cId].logs = [];
                    $scope.customers[cId].isUnread = true;
                    $scope.customers[cId].isConnected = true;
//                    if (!$scope.selectedCustomer) { This causes that after we ended one session, the next one will be buffered to same customer thus messages are 'invisible'
                    $scope.selectedCustomer = person;
//                    }
                } else {
                    var params = Object.keys(person);
                    params.forEach(function (param) {
                        $scope.customers[cId][param] = person[param];
                    });
                    $scope.customers[cId].isConnected = true;
                }

            }
        });
/*
        console.log('------------Update User Detail-------------');
        console.log($scope.customers);
*/
        if($scope.customers.length) {
            $scope.currentSubTab = $scope.customers[0].userID + '-summary';
        }
    });

    socket.on('joinedSuccessfully', function() {

        $scope.createRoom();

        var payload = {
            countrycode: '',
            device: ''
        };
        geolocation.getLocation().then(function(position) {
            return geolocation.getCountryCode(position);
        }).then(function(countryCode) {
            payload.countrycode = countryCode;
            return useragent.getUserAgent();
        }).then(function(ua) {
            return useragent.getIcon(ua);
        }).then(function(device) {
            payload.device = device;
            socket.emit('userDetails', payload);
        });
    });

    socket.on('disconnect', function(){
        $scope.status = 'offline';
        $scope.users = {};
    });


})

/* Directive for making bootstrap tab to blink
 *
 */
.directive('tabBlink', function() {
    return {
        restrict: 'A',
        scope: {
            connection: '='
        },
        link: function(scope, element, attrs) {
            scope.$watch('connection.isUnread', function () {
                if (scope.connection.isUnread) {
                    element.parent().removeClass();
                    element.parent().addClass('tab-blinking');
                } else {
                    element.parent().removeClass('tab-blinking');
                }
            });

            scope.$watch('connection.isConnected', function () {
                if (!scope.connection.isConnected) {
                    element.parent().removeClass();
                    element.parent().addClass('tab-disconnected');
                } else {
                    element.parent().removeClass('tab-disconnected');
                }
            });
        }
    };
})

.directive('modal', ['$rootScope', 'socket', '$sce', function ($rootScope, socket, $sce) {
    return {
        template: '<div class="modal fade">' +
        '<div class="modal-dialog">' +
        '<div class="modal-content">' +
        '<div class="modal-header">' +
        '<button type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>' +
        '<h4 class="modal-title">{{ title }}</h4>' +
        '</div>' +
        '<div class="modal-body"><div ng-bind-html="renderHtml(content)"></div><textarea ng-show="editing" class="editing-textarea" ng-model="edit_content"></textarea></div>' +
        '<div class="modal-footer">' +
        '<button type="button" class="btn btn-default" data-dismiss="modal">Close</button>' +
        '<button type="button" class="btn btn-primary" ng-click="editChatArticle()" ng-show="!editing">Edit</button>' +
        '<button type="button" class="btn btn-success" ng-click="saveChatArticle()" ng-show="editing">Save</button>' +
        '</div>' +
        '</div>' +
        '</div>' +
        '</div>',
        restrict: 'E',
        transclude: true,
        replace:true,
        scope:true,
        link: function postLink(scope, element, attrs) {
            scope.temp_contents = '';
            scope.editing = false;

            scope.$watch(attrs.visible, function(value){
                if(value == true)
                    $(element).modal('show');
                else
                    $(element).modal('hide');
            });

            scope.editChatArticle = function() {
                scope.edit_content = scope.content;
                scope.content = '';
                scope.editing = true;
            };

            scope.saveChatArticle = function() {
                socket.emit('saveChatBoxArticle', {tpl: $rootScope.chatArticleType, contents: scope.edit_content});
                scope.editing = false;
                scope.content = scope.edit_content;
            };

            scope.renderHtml = function (htmlCode) {
                return $sce.trustAsHtml(htmlCode);
            };

            $(element).on('shown.bs.modal', function(){

                scope.$apply(function(){
                    scope.editing = false;
                    scope.title = $rootScope.chatArticleType.charAt(0).toUpperCase() + $rootScope.chatArticleType.slice(1);
                    scope.$parent[attrs.visible] = true;
                    socket.emit('getChatBoxArticle', {tpl: $rootScope.chatArticleType}, function(data) {
                        scope.content = data;
                    });
                });
            });

            $(element).on('hidden.bs.modal', function(){

                scope.$apply(function(){
                    scope.$parent[attrs.visible] = false;
                });
            });
        }
    };
}]);
