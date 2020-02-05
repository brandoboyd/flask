(function () {
  'use strict';

  angular
    .module('slr.horizontal-timeline')
    .directive('horizontalTimeline', horizontalTimeline);

  /** @ngInject */
  function horizontalTimeline($timeout) {
    return {
      template: '<div id="timelineModal"></div>',
      restrict: 'E',
      scope: {
        source: '=',
        width: '@',
        height: '@',
        startZoomAdjust: '@',
        startAtEnd: '@',
        startAtSlide: '@',
        hashBookmark: '@',
        font: '@',
        lang: '@',
        thumbnailUrl: '@',
        state: '=',
        debug: '@',
        dayEvents: '=',
        showData: '&'
      },
      link: function postLink(scope, iElement, iAttrs) {

        var timeline;

        //////////////////////
        // Required config  //
        //////////////////////

        var width = (scope.width === undefined) ? '960' : scope.width;
        var height = (scope.height === undefined) ? '540' : scope.height;
        var timeline_conf = {
          source: scope.source
        };

        //////////////////////
        // Optional config  //
        //////////////////////

        // What are other types? not documented in TimelineJS
        // Not yet available for change to user
        if (scope.type) timeline_conf["type"] = scope.type;

        // is this used? First glance did not see effect of change
        // I don't think it is useful when passing id in object instantiation as below
        // Not yet available for change to user
        if (scope.embedId) timeline_conf["embed_id"] = scope.embedId;

        // First glance did not see the effect?
        // Not yet available for change to user
        if (scope.embed) timeline_conf["embed"] = scope.embed;

        if (scope.startAtEnd === 'true')
          timeline_conf["start_at_end"] = true;
        timeline_conf["start_at_end"] = false;

        if (scope.startZoomAdjust) timeline_conf["start_zoom_adjust"] = scope.startZoomAdjust;

        // Still need to observe how slide and startAtSlide with behave together
        // in practice. For now, put the burden on the programmer to use both correctly
        // startAtSlide should only be used to instantiate and slide
        // should only be used to reload.

        if (scope.startAtSlide) timeline_conf["start_at_slide"] = scope.startAtSlide;

        // working, but how to integrate with Angular routing?! Something to ponder
        (scope.hashBookmark === 'true') ? timeline_conf["hash_bookmark"] = true :
          timeline_conf["hash_bookmark"] = false;

        if (scope.font) timeline_conf["font"] = scope.font;
        if (scope.thumbnailUrl) timeline_conf["thumbnail_url"] = scope.thumbnailUrl;

        (scope.debug === 'true') ? VMM.debug = true : VMM.debug = false;

        /////////////////////////////
        // Custom Timeline Config  //
        /////////////////////////////

        scope.$watch('state.modal_open', function (newVal, oldVal) {
          // When timeline is loaded check if a CRUD modal is open for editing
          if (timeline && newVal !== oldVal) {
            timeline.set_config_item("modal_open", newVal);
          }
        });

        /////////////////////////
        // Rendering Timeline  //
        /////////////////////////

        var render = function (s) {
          // Source arrived but not yet init'ed VMM.Timelines
          if (s && !timeline) {
            timeline_conf["source"] = s;
            timeline = new VMM.Timeline('timelineModal', width, height);
            timeline.init(timeline_conf);
          } else if (s && timeline) {
            if (typeof scope.state !== 'undefined' && scope.state.index) {
              timeline.reload(s, scope.state.index);
            } else {
              timeline.reload(s);
            }
          }
        };

        // Async cases (when source data coming from services or other async call)
        scope.$watch('source', function (newSource, oldSource) {
          // Source not ready (maybe waiting on service or other async call)
          if (newSource !== oldSource) {

          }
        });

        // Non-async cases (when source data is already on scope)
        render(scope.source);

        // When changing the current slide *from the controller* without changing the
        // source data.
        scope.$watch('state.index', function (newState, oldState) {
          if (!newState == 'undefined') {
            return;
          }
          if (timeline && newState !== oldState) {
            timeline.get_config().current_slide = newState;
          }
        });

        /////////////////////////
        // Events of Interest  //
        /////////////////////////

        var updateState = function (e, callback) {
          // For some reason I have not investigated when using
          // 'keydown' events the current_slide is not yet
          // updated in the TimelineJS config. This is why
          // I delay the scope.state.index binding through
          // a simple $timeout callback with 0 delay.
          // Funny enough this does not manifest itself
          // with 'click' events.
          return $timeout(function () {
            if (typeof scope.state !== 'undefined') {
              scope.state.index = timeline.get_config().current_slide;
            }
          });
        };

        // set up index to the element
        var flags = angular.element('.marker .flag').toArray();
        _.each(scope.dayEvents, function (day, index) {
          angular.element(flags[index]).attr('data-day-index', index);
        });

        angular.element('.nav-next').on("click", function (e) {
          updateState(e);
          var index = angular.element('.marker.active').find('.flag').attr('data-day-index');
          scope.showData({index: index});
        });

        angular.element('.nav-previous').on("click", function (e) {
          updateState(e);
          var index = angular.element('.marker.active').find('.flag').attr('data-day-index');
          scope.showData({index: index});
        });

        iElement.on("click", ".marker", function (e) {
          var index = angular.element(this).find('.flag').attr('data-day-index');
          scope.showData({index: index});
          updateState(e);
        });

        var bodyElement = angular.element(document.body);
        bodyElement.on("keydown", function (e) {
          // On what keys to update current slide state
          // Might be missing some, touch keys?!?
          // Using object mapping for clarity
          var keys = {
            33: "PgUp",
            34: "PgDn",
            37: "Left",
            39: "Right",
            36: "Home",
            35: "End"
          };
          var keysProps = Object.getOwnPropertyNames(keys);
          if (keysProps.indexOf(e.keyCode + '') != -1) {
            updateState(e);
          }
        });

      }
    };
  }
})();