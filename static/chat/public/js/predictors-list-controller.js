(function() {
  'use strict';

  angular.module('journey')
    .controller('PredictorsListCtrl',
    ['$scope', 'AuthService', 'PredictorService',
    function($scope, AuthService, PredictorService) {
      $scope.predictors = [];
      $scope.SOCKET_DOMAIN = SOCKET_DOMAIN;

      $scope.init = function() {
        AuthService.authenticate({
          username: 'super_user@solariat.com',
          password: 'password'
        })
          .then(function(response) {
            $scope.token = response.data.token;
            return PredictorService.getAll($scope.token);
          })
          .then(function(response) {
            $scope.predictors = _.map(response.data.list, function(p) {
              return _.extend(p, {score: null, estimated_reward: null});
            });
          });
      };

      $scope.scoreWithPredictor = function(predictor, index) {
        var params = {
          // Agents
          actions: [
            {
              action_id: '',
              skill: '',
              age: '',
              fluency: '',
              seniority: ''
            }
          ],
          token: $scope.token,
          // Customer
          context: {
            age: '',
            gender: '',
            location: '',
            n_subs: '',
            intention: '',
            seniority: ''
          }
        };

        PredictorService.score(predictor, params)
          .then(function(res) {
            if (res.status === 200) {
              $scope.predictors[index].score = res.data.list[0].score;
              $scope.predictors[index].estimated_reward = Math.round(res.data.list[0].estimated_reward * 100) / 100;
            }
          })
      };

      $scope.init();
    }])
}());