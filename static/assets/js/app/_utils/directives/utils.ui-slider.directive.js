(function () {
  'use strict';

  angular
    .module('slr.utils')
    .directive('uiSlider', uiSlider);

  function uiSlider() {
      var default_config = {
        range: "max",
        min: 0,
        max: 1,
        step: 0.01
      };

      return {
        require: 'ngModel',
        link: function (scope, elm, attrs, ctrl) {
          //var config = scope.slider_config || default_config;
          var config = scope.slider_config || angular.extend({}, default_config, scope.$eval(attrs.uiSlider));
          var sliderElm = elm.slider(config, {
            slide: function (event, ui) {
              //we don't want update model onSlide
              elm.prev().val((ui.value));
            },
            stop: function (event, ui) {
              scope.$apply(function () {
                var v = config.range === true ? ui.values : ui.value;
                ctrl.$setViewValue(v);
              });
            }
          });

          scope.$watch(attrs.ngModel, function (newVal) {
            // in range slider, if newVal is invalid, ui will break, so handle most possible default values
            if (config.range === true) {
              if (!(newVal instanceof Array) || newVal.length === 0) {
                return;
              }
            }

            var sliderValue = config.range === true ? {values: newVal} : {value: newVal};
            sliderElm.slider(sliderValue);
          }, config.range === true);
        }
      };
    }
})();