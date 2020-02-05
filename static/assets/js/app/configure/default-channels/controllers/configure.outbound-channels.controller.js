(function() {
  'use strict';

  angular
    .module('slr.configure')
    .controller('OutboundChannelsCtrl', OutboundChannelsCtrl);

  /** @ngInject */
  function OutboundChannelsCtrl($scope, $resource, $routeParams, $timeout, $rootScope, $route, toaster) {
    $scope.defaultOutboundChannels = [];
    $scope.accountId = $routeParams.acct_id;
    $scope.selectedChannels = {};
    $scope.state = 'normal';

    $rootScope.$on('$viewContentLoaded', function(e) {
        $scope.header = $route.current.$$route.title;
        //console.log($scope.header);
    });

    var OutboundChannels = $resource('/configure/outbound_channels/json', {}, {
        //TODO: add user:"@user" to params
        fetch: { method:'GET', isArray:false, params:{account_id:"@account_id"}},
        update: { method:'POST', isArray:false, params:{account_id:"@account_id"} }
    });

    $scope.fetchOutboundChannelDefaults = function(account_id) {
        var res = OutboundChannels.fetch({account_id:account_id}, function(){
            $scope.defaultOutboundChannels = res.data;
            $scope.noDefaultOutboundChannels = _.isEmpty($scope.defaultOutboundChannels);
            for (var platform in $scope.defaultOutboundChannels) {
                var selected = _.find($scope.defaultOutboundChannels[platform], function(item) {return item.selected; });
                if (selected)
                    $scope.selectedChannels[platform] = selected.id;
            }
        });
    };

    $scope.updateOutboundChannelDefaults = function(account_id) {
        $scope.state = 'loading';
        OutboundChannels.update({account_id:account_id, oc:$scope.selectedChannels}, function() {
            // Close Dialog
            $scope.modalShown = false;
            toaster.pop('success', 'Default Channels successfully changed.');
        }).$promise.finally(function(){
              $scope.state = 'loaded';
              $timeout(function(){$scope.state="normal";}, 2000);
          });
    };

    //$scope.watch('modalShown', function(visible, oldValue) {
    //   if (visible) {
    //       $scope.fetchOutboundChannelDefaults($scope.accountName);
    //   }
    //});

    $scope.fetchOutboundChannelDefaults($scope.accountId);
}
})();