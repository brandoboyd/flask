(function () {
  'use strict';

  angular
    .module('slr.configure')
    .factory('EventsList', EventsList);

  /** @ngInject */
  function EventsList($http) {
    return {
      list: function (params) {
        var promise = $http({
          method: 'GET',
          url: '/events/json',
          params: params
        }).then(function (res) {
          return res.data;
        });
        return promise;
      },
      getById: function (event_id) {
        return $http({
          method: 'GET',
          url: '/events/json',
          params: {id: event_id}
        }).then(function (res) {
          //console.log(res);
          return res.data.item;
        });
      }
    };
  }
})();