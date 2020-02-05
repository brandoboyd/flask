'use strict'
angular.module('journey')
    .controller('DemoIndexCtrl', ['$scope', '$location', '$window', '$modal', '$http', 'socket', 'ChannelsService', 'EventsService',
        function ($scope, $location, $window, $modal, $http, socket, ChannelsService, EventsService) {

            $scope.token = null;
            $scope.sessionIds = {};

            $scope.goToSupervisor = function() {
                var wUrl = ('http://{{HOST_DOMAIN}}/journey/supervisor').replace("{{HOST_DOMAIN}}", HOST_DOMAIN);
                $window.open(wUrl, '_blank');
            };

            $scope.goToAnonymous = function() {
                var wUrl = ('http://{{SOCKET_DOMAIN}}/landing/anonymous').replace("{{SOCKET_DOMAIN}}", SOCKET_DOMAIN);
                $window.open(wUrl, '_blank');
            };

            $scope.resetAll = function() {
                socket.emit('resetAllCustomers');
            };

            socket.on('sendDiagnostics', function(data) {
                $scope.$broadcast('receivedDiagnostics', data);
            });

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

            socket.on('resetFinished', function() {
                var modalInstance = $modal.open({
                    templateUrl: 'reset-confirm-modal.html',
                    controller: 'ModalInstanceCtrl',
                    resolve: {
                        title: function () {
                            return 'Success';
                        },
                        content: function () {
                            return 'All chat sessions has been reset!';
                        }
                    }
                });

                modalInstance.result.then(function () {
                }, function () {
                });
            });

            socket.on('customerInitialChatMessage', function(data, callback) {
                console.log("Customer initial chat data -----> ", data);

                socket.emit('getSessionId', data.from, function(computedSessionId) {
                    console.log("ON DEMO INDEX GOT SESSION ", computedSessionId);
                    ChannelsService.getByPlatform($scope.token, 'chat')
                      .then(function(channels) {

                        var channel_id = channels.data.list[0].id;

                        EventsService.postEvent(
                          {
                            content   : data.message,
                            channels  : [channel_id],
                            token     : $scope.token,
                            type      : 'chat',
                            is_inbound: true,
                            session_id: computedSessionId,
                            actor_id  : data.from //message.userId
                          })
                          .then(function (data) {
                            console.log("Initial customer post from Customer was submitted", data);
                            //return ChatSummaryService.getById($scope.token, data.customer_id)
                            //$scope.nextBestActionChat(data);
                            //$scope.setChatSummary(data);
                            callback(data);
                          });
                      });
                });

            });

            socket.on('webClickActions', function(data) {
                console.log("Customer click action data -----> ", data);

                var eventId = null,
                    customerId = null;

                ChannelsService.getByPlatform($scope.token, 'web')
                    .then(function(response) {
                        console.log("Channels", response);
                        if (response.data.list.length > 0) {
                            var channel = response.data.list[0];
                            var apiUrl = ('http://{{HOST_DOMAIN}}/api/v2.0/events').replace('{{HOST_DOMAIN}}', HOST_DOMAIN);
                            return $http.post( apiUrl, {
                                url       : data.action,   // Bit of a hack but it will work anyway
                                channels  : [channel.id],
                                token     : $scope.token,
                                type      : 'web',
                                is_inbound: true,
                                journey_stages : data.journeyInfo,
                                actor_id  : data.isAnonymous ? null : data.userId,
                                native_id : data.isAnonymous ? data.userId : null
                            });
                        }
                    })
                    .then(function(response) {
                        console.log("Click by Customer was submitted, got data:", response.data);
                        var apiUrl = ('http://{{HOST_DOMAIN}}/api/v2.0/next_best_action/query').replace('{{HOST_DOMAIN}}', HOST_DOMAIN);
                        if (!data.userAcceptedChat) {
                            eventId = response.data.item.id;
                            return $http.post(apiUrl, {
                                token: $scope.token,
                                event_id: response.data.item.id,
                                customer_id: data.isAnonymous ? response.data.item.actor_id : data.userId,
                                event_type: 'web'
                            });
                        }
                    })
                    .then(function(response) {
                        if (response.status === 200 && !!response.data.list && !!response.data.list.length) {
                            console.log("Next best actions: ", response.data);

                            var bestAction = response.data.list[0];
                            if (bestAction.name !== 'Do Nothing') {
                                socket.emit('offerChatToCustomer', {
                                    userId: data.userId,
                                    eventId: eventId,
                                    actionId: bestAction.id,
                                    customerId: response.data.customer_id,
                                    message: bestAction.name
                                });
                            }
                        }
                    });
            });

            socket.on('rateWebClickActions', function(data) {
                var apiUrl = ('http://{{HOST_DOMAIN}}/api/v2.0/next_best_action/feedback').replace("{{HOST_DOMAIN}}", HOST_DOMAIN);
                $http.post(apiUrl, {
                    token       : $scope.token,
                    action_id   : data.actionId,
                    event_id    : data.eventId,
                    score       : data.score,
                    customer_id : data.customerId,
                    event_type  : 'web'
                }).then(function(response) {
                    if (response.status === 200) {
                        console.log('Successfully sent feedback for next_best_action');
                    }
                });
            });

            $scope.init = function() {
                socket.emit('getToken', {}, function(data) {
                    $scope.token = data.token;
                });
            };


            $scope.doStateRecover = function(event) {
                var apiUrl = ("http://{{HOST_DOMAIN}}/api/v2.0/demo/{{event}}")
                                .replace("{{HOST_DOMAIN}}", HOST_DOMAIN)
                                .replace("{{event}}", event);
                $http.post(apiUrl, {token : $scope.token})
                    .success(function(data) {
                        console.log(data);
                        alert("System " + event + " complete");
                    });
            }

            $scope.init();
        }])

    .controller('ModalInstanceCtrl', ['$scope', '$modalInstance', 'title', 'content',
        function ($scope, $modalInstance, title, content) {
            $scope.body = {
                'title' : title,
                'content': content
            };

            $scope.ok = function () {
                $modalInstance.close();
            };

            $scope.cancel = function () {
                $modalInstance.dismiss('cancel');
            };
        }]);
