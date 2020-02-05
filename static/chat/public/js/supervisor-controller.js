'use strict'
angular.module('chat')
    .controller('SupervisorCtrl',
        function ($scope, $rootScope, $modal, $http, $state, socket, AuthService, AgentService, ChannelsService) {

            $scope.token = null;
            $scope.agents = [];
            $scope.alertsInfo = {};

            var typing = false;
            var timeout  = undefined;
            var userNames = {
                0: 'Agent',
                1: 'Customer',
                2: 'ChatBot',
                3: 'Me'
            };

            $scope.gridsterOptions = {
                margins: [10, 10],
                columns: 4,


                resizable: {
                    enabled: true,
                    handles: ['n', 's', 'w', 'ne', 'se', 'sw', 'nw'],
                    stop: function (e) {
                        scope.resize(e);
                    }
                },

                draggable: {
                    enabled: true,
                    handle: '.box-header'
                }
            };

            $scope.init = function() {
                socket.emit('getToken', {}, function(data) {
                    $scope.token = data.token;
                    ChannelsService.getByPlatform($scope.token, 'chat')
                      .then(function(channels) {
                          $scope.channel_id = channels.data.list[0].id
                          AgentService.getAll($scope.token)
                            .then(function(response) {
                                _.each(response.data.list, function(agent) {
                                    $scope.agents.push({
                                        name: agent.name,
                                        sizeX: 2,
                                        sizeY: 1,
                                        detail: agent,
                                        typer: null,
                                        messages: []
                                    });
                                });

                            })
                    })

                });
            };

            $scope.isSummariesLoaded = false;

            $scope.$watch('agents.length', function(nVal, oVal) {
              if(nVal > oVal) {
                var agentsId = _.map($scope.agents, function(agent) {
                  return agent.detail.id
                });
                var apiUrl = ('http://{{HOST_DOMAIN}}/api/v2.0/chat/summary').replace("{{HOST_DOMAIN}}", HOST_DOMAIN);
                $http.post(apiUrl,
                  {
                    token: $scope.token,
                    agents_ids: agentsId,
                    channel_id:$scope.channel_id
                  }
                ).success(function(data) {
                  var summaries = data.list;
                      _.each(summaries, function(s){
                          var s_key = _.keys(s)[0];
                          var a = _.find($scope.agents, function(agent) {
                              return agent.detail.id === s_key
                          })
                          a.summaries = s[s_key].reverse();
                          if (a.summaries.length > 3) {
                              a.sizeY = 2
                          }
                      })
                      $scope.isSummariesLoaded = true;
                })
              }
            })

            socket.on('connectingToSocketServer', function(data) {
                socket.emit('joinSocketServer', {
                    userID: 'supervisor',
                    userName: 'Super Admin',
                    userSex: 'N/A',
                    userAge: 'N/A',
                    userSegment: 'N/A',
                    userType: 'supervisor'
                });
            });

            socket.on('askToSupervisor', function(agentInfo) {
                var alertData = agentInfo['alert_data'];
                $scope.alertsInfo[agentInfo.customer.id] = alertData;
                console.log("ASK SU TO JOIN", agentInfo)
                var agent = _.findWhere($scope.agents, {detail: {id: agentInfo.id}});
                if (agent) {
                    agent.roomId = agentInfo.roomId;
                    agent.customer = agentInfo.customer;
                    agent.latest_event_id = agentInfo.alert_data.event_id;
                    //socket.emit('joinRoom', agentInfo.roomId);
                }
                console.log(agent)
            });

            $scope.joinChat = function(agent) {
                agent.showChat = true;
                var summary = _.findWhere(agent.summaries, {latest_event_id: agent.latest_event_id});
                if (summary) {

                    agent.messages = [];
                    agent.summary = summary;
                    angular.forEach(summary.list, function(message) {
                        agent.messages.push({
                            sender  : (message.is_inbound)? 'Customer': 'Me',
                            body    : message.content
                        });
                    });
                }
                socket.emit('joinRoom', {type: 'supervisor', 'roomId': agent.roomId});
                agent.sizeX = 4;
                agent.sizeY = 2;
            }

            $scope.dismissChat = function(agent, isFeedback) {
                agent.roomId = null;
                //socket.emit('leaveRoom', {type: 'supervisor', 'roomId': agent.roomId});
                agent.showChat = false;
                agent.sizeX = 2;

                if (isFeedback) {
                    var alertData = $scope.alertsInfo[agent.customer.id]
                    if (alertData.action_id) {
                        var apiUrl = ('http://{{HOST_DOMAIN}}/api/v2.0/next_best_action/feedback').replace("{{HOST_DOMAIN}}", HOST_DOMAIN);
                        $http.post(apiUrl, {
                            token       : $scope.token,
                            action_id   : alertData.action_id,
                            event_id    : alertData.event_id,
                            score       : 0,
                            customer_id : alertData.customer_id,
                            event_type  : 'chat'
                        }).then(function(response) {
                            if (response.status === 200) {
                                console.log('Successfully sent negative feedback for supervisor alert');
                            }
                        });
                    } else {
                        console.log("Waiting for post in session to load next best action.")
                    }
                    if (alertData.do_nothing_id) {
                        var apiUrl = ('http://{{HOST_DOMAIN}}/api/v2.0/next_best_action/feedback').replace("{{HOST_DOMAIN}}", HOST_DOMAIN);
                        $http.post(apiUrl, {
                            token       : $scope.token,
                            action_id   : alertData.do_nothing_id,
                            event_id    : alertData.event_id,
                            score       : 1,
                            customer_id : alertData.customer_id,
                            event_type  : 'chat'
                        }).then(function(response) {
                            if (response.status === 200) {
                                console.log('Successfully sent positive feedback for doing nothing');
                            }
                        });
                    } else {
                        console.log("Waiting for post in session to load next best action.")
                    }
                }
            }

            $scope.send = function(agent) {
                if (typeof this.message === 'undefined' || (typeof this.message === 'string' && this.message.length === 0)) {
                    $scope.error.send = 'Please enter a message';
                } else {
                    socket.emit('send', {
                        senderType: 3,
                        from: 'supervisor',
                        toRoom: agent.roomId,
                        message: this.message
                    });
                    this.message = '';
                }
            };

            $scope.focus = function(bool) {
                $scope.focussed = bool;
            };

            $scope.typing = function(event, room) {
                function timeoutFunction() {
                    typing = false;
                    socket.emit('typing', {
                        senderType  : 3,
                        isTyping    : false,
                        from        : 'supervisor',
                        toRoom        : room
                    });
                }
                if (event.which !== 13) {
                    if (typing === false && $scope.focussed && room !== null) {
                        typing = true;
                        socket.emit('typing', {
                            senderType  : 3,
                            isTyping    : true,
                            from        : 'supervisor',
                            toRoom      : room
                        });
                        clearTimeout(timeout);
                        timeout = setTimeout(timeoutFunction, 500);
                    }
                }
            };

            socket.on('isTyping', function(data) {
                var agent = _.findWhere($scope.agents, {roomId: data.toRoom});
                if (data.from != 'supervisor') {
                    agent.typer = userNames[data.senderType];
                    agent.isTyping = data.isTyping;
                }
            });


            socket.on('sendChatMessage', function(data) {
                var message = {
                    sender  : userNames[data.senderType],
                    from    : data.from,
                    body    : data.message
                };

                var agent = _.findWhere($scope.agents, {roomId: data.toRoom});

                if (agent) {
                    agent.messages.push(message);
                }
            });

            socket.on('notifySupervisor', function(data, callback) {
                console.log("Super was NOTIFIED! ", data);

                var agent = _.find($scope.agents, function(a) { return a.detail.id === data.agent.id})
                console.log("AGENT WAS FOUND", agent)

                if (agent) {
                    $scope.isSummariesLoaded = false;
                    var apiUrl = ('http://{{HOST_DOMAIN}}/api/v2.0/chat/summary').replace("{{HOST_DOMAIN}}", HOST_DOMAIN);
                    $http.post(apiUrl,
                      {
                          token: $scope.token,
                          agents_ids: [agent.detail.id],
                          channel_id:$scope.channel_id
                      }
                    ).success(function(data) {
                          var summaries = data.list;
                          agent.summaries = summaries[0][agent.detail.id].reverse();
                          $scope.isSummariesLoaded = true;
                    })
                }
            });



            $scope.init();




            $scope.showConvo = function (summary) {

                var modalInstance = $modal.open({
                    templateUrl: 'myModalContent.html',
                    controller: ModalInstanceCtrl,
                    resolve: {
                        summary: function () {
                            return summary;
                        }
                    }
                });

                modalInstance.result.then(function () {

                }, function () {
                    console.log('Modal dismissed at: ', new Date());
                });
            };


        })






    .controller('AgentDetailCtrl', ['$scope', '$rootScope', '$stateParams', '$state', 'AuthService', 'AgentService',
        function ($scope, $rootScope, $stateParams, $state, AuthService, AgentService) {

            $scope.remove = function(agent) {
                console.log("Remove agent - " + agent.name);
            };

        }])


var ModalInstanceCtrl = function ($scope, $modalInstance, summary) {

    console.log("show demo", summary);

    $scope.summary = summary;


    $scope.ok = function () {
        $modalInstance.close();
    };

    $scope.cancel = function () {
        $modalInstance.dismiss('cancel');
    };
};