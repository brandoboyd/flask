(function(){
    'use strict';

    angular.module('journey').controller('CustomersListCtrl', ['$scope', '$http', '$window', 'AuthService', 'CustomerService',
        function ($scope, $http, $window, AuthService, CustomerService){
            $scope.customers = [];
            $scope.SOCKET_DOMAIN = SOCKET_DOMAIN;
            $scope.init = function() {
                AuthService.authenticate({
                    username: 'super_user@solariat.com',
                    password: 'password'
                })
                    .then(function(response) {
                        console.log(response)
                        $scope.token = response.data.token;
                        return CustomerService.getAll($scope.token);
                    })

                    .then(function(response) {
                        $scope.customers = response.data.list;
                    });
            };
            $scope.init();

        }])
}());