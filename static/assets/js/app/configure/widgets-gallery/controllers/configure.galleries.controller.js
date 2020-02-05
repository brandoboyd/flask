(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('GalleriesCtrl', GalleriesCtrl);

  /** @ngInject */
  function GalleriesCtrl($scope, $http) {
    var init = function () {
      $http.get('/gallery')
        .success(function (galleries) {
          $scope.galleries = galleries.data;
        });

      $scope.filters = {display_name: ''};
    };

    init();
  }
})();