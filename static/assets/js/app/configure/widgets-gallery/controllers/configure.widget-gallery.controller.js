(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('WidgetsGalleryCtrl', WidgetsGalleryCtrl);

  /** @ngInject */
  function WidgetsGalleryCtrl($scope, $http, $routeParams) {
    var init = function () {
      $http.get('/gallery/' + $routeParams.id)
        .success(function (res) {
          $scope.gallery = res.data;
        });
      $scope.filters = {title: ''};
      $scope.selected = [];
      $scope.table = {
        sort: {
          predicate: 'title',
          reverse: false
        }
      };
    };

    $scope.selectModel = function (model) {
      if ($scope.selected.length) {
        var i = $scope.selected.indexOf(model);
        if (i === -1) {
          $scope.selected.push(model);
        } else {
          $scope.selected.splice(i, 1);
        }
      } else {
        $scope.selected.push(model);
      }
    };

    $scope.remove = function () {
      _.each($scope.selected, function (model) {
        $http.delete('/gallery/' + $routeParams.id + '/widget_models/' + model.id)
          .success(function () {
            _.remove($scope.gallery.widget_models, {'id': model.id});
          });
      });
    };

    init();
  }
})();