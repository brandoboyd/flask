(function () {
  'use strict';

  angular.module('omni')
    .directive('journeyTimeline', journeyTimeline);

  function journeyTimeline($modal, $http) {
    return {
      restrict: 'A',
      scope: {
        journeyTimeline: '@',
        journeyTimelineParams: '@'
      },
      link: function (scope, el) {
        el.bind('click', function () {
          var journey, params;

          try {
            journey = JSON.parse(scope.journeyTimeline); // item from customer/journey
            params = JSON.parse(scope.journeyTimelineParams); // contains journey tags

          } catch (e) {
            console.error(e);
            return;
          }

          $http.post('/customer/journeys', {
              customer_id: params.customer_id,
              from: params.from,
              to: params.to
            })
            .success(function (data) {
              if (data.journeys.length) {
                if (_.has(params, 'assignedTags')) {
                 _.extend(journey, {assignedTags: params.assignedTags});
                }
                if (_.has(params, 'journey_stages')) {
                 _.extend(journey, {journey_stages: params.journey_stages});
                }

                $modal.open({
                  scope: scope.$new(),
                  templateUrl: '/static/assets/js/app/omni/directives/journey-timeline/omni.journey-timeline.html',
                  controller: TimelineController,
                  size: 'lg',
                  windowClass: 'app-modal-window',
                  resolve: {
                    journeys: function () {
                      return data.journeys;
                    },
                    selected: function () {
                      return journey;
                    }
                  }
                });
              }
            });
        });

        function TimelineController($scope, $modalInstance, journeys, selected, JourneysTimelineFactory,
                                           $http, $timeout, $q, $location, $anchorScroll) {
          $scope.flags = resetFlags();

          if (angular.isDefined(selected)) {
            $scope.assignedTags = selected.assignedTags;
          }

          function getJourneys() {
            var deferred = $q.defer();
            var items = {
              customer: {},
              journeys: []
            };

            _.each(journeys, function (journey) {
              $http.get('/journey/' + journey.id + '/stages')
                .success(function (data) {
                  _.extend(data.item.journey, {typeId: journey.typeId});
                  items.customer = data.item.customer;
                  items.journeys.push(data.item.journey);

                  if (items.journeys.length === journeys.length) {
                    deferred.resolve(items);
                  }
                });
            });

            return deferred.promise;
          }

          function getDefaultStageIndex() {
            // get first selected stage in facet list
            var rv = 0;
            if (angular.isDefined(selected.journey_stages)) {
              _.each(selected.journey_stages.list, function (stage) {
                if (stage.enabled) {
                  // selected stage might not be present in the current journey
                  rv = _.findIndex($scope.journey.stages, {stageName: stage.display_name});
                  if (rv > -1) {
                    return true;
                  }
                }
              });
            }
            // journey timeline might contain journeys that do not match the filter criteria at all
            // so in case selected jouney do not contain filtered stage, set first stage as default stage
            if (rv === -1) {
              rv = 0;
            }
            return rv;
          }

          function getStages(index) {
            $scope.journey = $scope.journeys[index];
            $scope.outcome = JourneysTimelineFactory.buildOutcome($scope.journey);

            $timeout(function () {
              var decorator = angular.element('.decoratorStage');
              var arr = decorator.toArray();
              decorator.removeClass('finished-back');
              decorator.removeClass('abandoned-back');
              angular.element(arr[arr.length - 1]).addClass($scope.journey.status + '-back');
            }, 50);

            getEvents(getDefaultStageIndex());

            $timeout(function () {
              /** SCORES VISUALIZATION BUILD */
              if ($scope.journey.NPS !== null && $scope.journey.CSAT !== null) {
                JourneysTimelineFactory.buildVisualization($scope.journey);
              }
            }, 50);
          }

          function getEvents(index) {
            $scope.selectedStage = $scope.journey.stages[index];
            $scope.flags.isEventsFetched = true;
            JourneysTimelineFactory.getEvents(index, $scope.journey, function (res) {
              $scope.stage = res.stage;
              $scope.flags.isEventsFetched = false;
              $scope.verticalTimeline = res.verticalTimeline;
            });
          }
;
          getJourneys().then(function (items) {
            $scope.journeys = _.sortBy(items.journeys, 'startDate');
            $scope.customer = items.customer;
            // $scope.customer_name = $scope.customer.customer_full_name ? $scope.customer.customer_full_name
            //   : $scope.customer.first_name + ' ' + $scope.customer.last_name;
            // $scope.customer = _.omit($scope.customer, ['full_name', 'last_name', 'first_name', 'customer_full_name']);

            $scope.verticalTimeline = [];
            $scope.outcome = '';

            /** Horizontal Timeline - Journeys */
            if ($scope.journeys.length) {
              _.each($scope.journeys, function (journey, index) {
                $scope.journeys[index].startDate = moment(journey.startDate).format('YYYY-MM-DD');
                $scope.journeys[index].endDate = moment(journey.endDate).format('YYYY-MM-DD');
                _.extend(journey, {headline: journey.type});
              });

              var journeyDateRange = {
                startDate: $scope.journeys[0].startDate, // min
                endDate: $scope.journeys[$scope.journeys.length - 1].endDate // max
              };

              $scope.horizontalTimeline = JourneysTimelineFactory.buildHorizontalTimeline($scope.journeys, journeyDateRange);
              $scope.zoomAdjust = $scope.journeys.length - 1;

              if (angular.isDefined(selected)) {
                var found = _.findWhere($scope.journeys, {id: selected.id});
                $scope.startAt = angular.isDefined(found) ? $scope.journeys.indexOf(found) : 0;
                getStages($scope.startAt);
              } else {
                $scope.startAt = 1;
                getStages(0);
              }

            } else {
              $scope.flags.showEmptyMsg = true;
            }
          });

          // show stages
          $scope.showData = function (index) {
            if (index || index === 0) {
              getStages(index);
            } else {
              $scope.flags.showErrMsg = true;
            }
          };

          $scope.showEvents = function (index) {
            if (index || index === 0) {
              getEvents(index);
            } else {
              $scope.flags.showErrMsg = true;
            }
          };

          $scope.showEventContent = function (index) {
            $timeout(function () {
              angular.element('.' + index).slideToggle();
            });
          };

          $scope.getEventAssignedTagId = function (event, index) {
            var found = _.findWhere(event.assignedTags, {index: (index)});
            if (typeof found !== 'undefined') {
              return found.id;
            }
          };

          $scope.navigateToTag = function (id) {
            var found = angular.element('[id*="' + id + '"]');
            found.show();

            var foundId = found.attr('id');

            $location.hash(foundId);
            $anchorScroll();
            angular.element('#' + foundId).addClass('highlighter');
            $timeout(function () {
              angular.element('#' + foundId).removeClass('highlighter');
            }, 500);
          };

          $scope.getNPSIcon = function (event) {
            var nps = event.content[0].reward_data.nps;

            if (nps >= 9) {
              return 'face-happy';
            } else if (7 < nps && nps > 9) {
              return 'face-neutral';
            } else if (nps < 7) {
              return 'face-sad';
            } else {
              return 'face-unknown';
            }
          };

          function resetFlags() {
            return {
              showErrMsg: false,
              showEmptyMsg: false,
              isEventsFetched: false,
              stagesPipeline: true
            }
          }

          $scope.close = function () {
            $modalInstance.dismiss('close');
          };
        }
      }
    }
  }
})();