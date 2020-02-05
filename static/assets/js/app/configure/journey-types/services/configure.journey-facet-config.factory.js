(function () {
  'use strict';

  angular
    .module('slr.configure')
    .factory('JourneyFacetConfig', JourneyFacetConfig);

  /** @ngInject */
  function JourneyFacetConfig($http, $q) {
    var _cachedOptions = null;
    var platforms = ['twitter', 'facebook', 'nps', 'chat', 'email', 'web', 'voice'];

    return {
      "getOptions": function (callback) {
        var result;
        if (_cachedOptions !== null) {
          result = $q.when(_cachedOptions);
        } else {
          result = $http.get('/journeys/facet_options').then(function (resp) {
            _cachedOptions = resp.data;
            return _cachedOptions;
          });
        }
        if (callback && angular.isFunction(callback)) {
          return result.then(callback);
        }
        return result;
      },
      "getEventTypes": function (callback) {
        var result;
        var promises = [];
        if (_cachedOptions && _cachedOptions.eventTypes !== null) {
          result = $q.when(_cachedOptions);
        } else {
          //fetch dynamic and static events {show_all:true}
          var event_type_promise = $http.get('/event_type/list', {
            params : { show_all : true }
          });
          promises = [event_type_promise];

          result = $q.all(promises).then(function (responses) {
            var types = [];
            _.each(responses, function (resp) {
              if (!resp.data) return;
              types = types.concat(_.map(resp.data.data, function (type) {
                return {
                  'id': type.id,
                  'name': type.name,
                  'platform' : type.platform,
                  'display_name' : type.name
                };
              }));
            });
            _cachedOptions.eventTypes = types;
            return _cachedOptions;
          });
        }
        if (callback && angular.isFunction(callback)) {
          return result.then(callback);
        }
        return result;
      },
      "makeFilter": function (scope) {
        var keys = _.keys(_.pick(scope, 'display_name', 'description', 'title'));
        return _.object(keys, ['', '', '']);
      }
    };
  }
})();