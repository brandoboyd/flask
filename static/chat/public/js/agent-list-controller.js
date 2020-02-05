'use strict'
angular.module('journey')
    .controller('AgentListCtrl', ['$scope', '$rootScope', '$stateParams', '$state', 'AuthService', 'AgentService',
        function ($scope, $rootScope, $stateParams, $state, AuthService, AgentService) {

            $scope.agents = [];
            $scope.token = '';

            $scope.init = function () {

                AuthService.authenticate({
                        username: 'super_user@solariat.com',
                        password: 'password'
                })
                    .then(function(response) {
                        $scope.token = response.data.token;
                        return AgentService.getAll($scope.token);
                    })

                    .then(function(response) {
                        $scope.agents = angular.copy(response.data.list);
                    });
            };




            $scope.gotoAgentDetail = function(id) {
                $state.go('agents.desktop', {'agentId': id});
            }

            $scope.init();

        }]);
