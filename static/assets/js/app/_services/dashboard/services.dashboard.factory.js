(function () {
  'use strict';

  angular
    .module('slr.services')
    .factory('DashboardService', DashboardService)
    .factory('WidgetService', WidgetService);

  /** @ngInject */
  function DashboardService($http, $q) {
    var dashboards = {
      'types': [],
      'list': {},
      'load': load,
      'loadSimple': loadSimple
    };
    return dashboards;

    function load() {
      var defer = $q.defer();
      $q.all([
        $http.get('/dashboards/type'),
        $http.get('/dashboards')
      ]).then(function (res) {
        dashboards.types = res[0].data.data;
        _.each(dashboards.types, function (type) {
          dashboards.list[type.id] = _.filter(res[1].data.data, {'type_id': type.id});
        });
        defer.resolve({
          'types': dashboards.types,
          'list': dashboards.list
        })
      }, function (err) {
        dashboards.types = [];
        dashboards.list = {};
        defer.reject('Failed to get dashboards!');
      });
      return defer.promise;
    }

    function loadSimple() {
      var defer = $q.defer();
      $q.all([
        $http.get('/dashboards/type'),
        $http.get('/dashboards')
      ]).then(function (res) {
        dashboards.types = _.map(res[0].data.data, _.partialRight(_.pick, ['id', 'display_name']));
        _.each(dashboards.types, function (type) {
          var list = _.filter(res[1].data.data, {'type_id': type.id});
          dashboards.list[type.id] = _.map(list, _.partialRight(_.omit, 'widgets'));
        });
        defer.resolve({
          'types': dashboards.types,
          'list': dashboards.list
        })
      }, function (err) {
        dashboards.types = [];
        dashboards.list = {};
        defer.reject('Failed to get dashboards!');
      });
      return defer.promise;
    }
  }

  /** @ngInject */
  function WidgetService($http, $location, $q, $rootScope, $timeout) {
    var current = null,
      CHANGED = 'WidgetService.CHANGED';

    function notify() {
      $rootScope.$broadcast(CHANGED, {widget: current});
    }

    return {
      CHANGED: CHANGED,
      getCurrent: function () {
        return current;
      },
      setCurrent: function (widget) {
        current = widget;
        notify();
      },
      load: function (wid) {
        var self = this;
        return $http({method: 'GET', url: '/dashboard/' + wid + '/widget'}).then(function (res) {
          self.setCurrent(res.data.item);
          return current;
        });
      },
      loadFromLocation: function () {
        var params = $location.search();
        if (params['wid']) {
          return this.load(params['wid']);
        } else {
          return $q.when(null);
        }
      },
      create: function (widget) {
        var fields = ['title', 'description', 'style', 'settings', 'extra_settings', 'dashboard_id'],
          data = _.pick(widget, fields),
          newWidgetURL = '/dashboard/new';
        return $http({method: 'POST', url: newWidgetURL, data: data});
      },
      update: function (widget) {
        var updateWidgetURL = "/dashboard/" + widget.id + "/update",
          self = this;
        return $http({method: 'POST', url: updateWidgetURL, data: widget}).then(function (res) {
          self.setCurrent(res.data.item);
        });
      },

      makeRemove: function (lock, lockParam) {
        var self = this;
        return function () {
          lock[lockParam] = true;
          $timeout(function () {
            $location.search('wid', null);
            $timeout(function () {
              lock[lockParam] = false;
            }, 10);
          }, 0);

          self.setCurrent(null);
        };
      }
    }
  }
})();