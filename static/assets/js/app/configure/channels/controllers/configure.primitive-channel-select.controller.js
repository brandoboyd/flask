(function() {
  'use strict';

  angular
    .module('slr.configure')
    .controller('PrimitiveChannelSelectCtrl', PrimitiveChannelSelectCtrl);

  /** @ngInject */
  function PrimitiveChannelSelectCtrl($scope, CompoundChannelService){
        $scope.options = {
            'selected': [],
            'options': []
        };

        var filterOptionsByPlatform = function(force) {
            $scope.options = CompoundChannelService.filterOptionsByPlatform($scope.options, force);
        };

        var setup = function() {
            var compound = CompoundChannelService.compound;
            if (compound)
                $scope.options.selected = _.pluck(compound.primitive_channels, 'id');

            filterOptionsByPlatform(true);
        };

        if (CompoundChannelService.isReady()) {
            setup();
        } else {
            $scope.$on(CompoundChannelService.LOADED, setup);
        }

        $scope.$watch('options.selected', function(newValue, oldValue){
            if (newValue != oldValue) {
                filterOptionsByPlatform();
                CompoundChannelService.primitivesChanged([{key: 'primitive_channels', value: newValue}]);
            }
        }, true);
    };
})();