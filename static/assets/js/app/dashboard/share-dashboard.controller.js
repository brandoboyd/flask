(function() {
  'use strict';
  angular.module('dashboard')
    .controller('ShareDashboardCtrl', function($scope, $modalInstance, dashboard, $http, AccountsService) {

      var init = function() {
        $scope.fetchUsers();
      };

      $scope.filters = {
        searchQuery: ''
      };

      var debouncedFetchUsers = _.debounce(function () {
          $scope.fetchUsers();
      }, 500);

      $scope.$watch('filters.searchQuery', function (n, o) {
          if (!n && !o) {
              return;
          }
          debouncedFetchUsers();
      });

      $scope.chosenUsers = _.clone(dashboard.shared_to);

      $scope.toggled = function (user) {
        if (user.chosen) {
          $scope.chosenUsers.push(user.id);
        } else {
          _.pull($scope.chosenUsers, user.id);
        }
      };

      $scope.fetchUsers = function () {
        var params = {
          offset: $scope.pagination.offset,
          limit: $scope.pagination.limit,
          account: dashboard.accountId
        };

        if ($scope.filters.searchQuery) {
            params.searchQuery = $scope.filters.searchQuery;
        }

        $http.get('/configure/account/userslist', {params: params})
          .success(function (result) {
            $scope.pagination.totalItems = result.total_items;
            $scope.pagination.pages = result.pages;

            _.remove(result.users, {self: true});
            $scope.users = _.map(result.users, function (user) {
              var chosen = $scope.chosenUsers.indexOf(user.id) > -1;
              return _.extend(user, {chosen: chosen});
            });

          });
      };

      $scope.pagination = {
          offset: 0,
          limit: 10,
          currentPage: 1,
          totalItems: 0,
          pages: 0,
          maxSize: 10,
          setPage: setPage
      };

      function setPage() {
          $scope.pagination.offset = parseInt($scope.pagination.limit) * ($scope.pagination.currentPage - 1);
          $scope.fetchUsers();
      }

      $scope.share = function() {
        $http.put('/dashboards/' + dashboard.id,
          {shared_to: $scope.chosenUsers}
        ).success(function (res) {
          $modalInstance.close();
          dashboard.shared_to = $scope.chosenUsers;
        });
      };

      init();
    });
}());
