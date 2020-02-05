(function(){
    'use strict';

    angular.module('journey').controller('StatsCtrl', ['$scope', 'socket',
        function ($scope, socket) {

            $scope.rooms = [];

            $scope.init = function() {
                socket.emit('sendDiagnostics', {});
            };

            $scope.refresh = function() {
                socket.emit('sendDiagnostics', {});
            }

            $scope.$on('receivedDiagnostics', function(evt, openRooms) {
                $scope.rooms = angular.copy(openRooms);
            });

            $scope.init();
        }])
}());


