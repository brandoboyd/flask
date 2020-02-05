(function () {
  'use strict';

  angular
    .module('slr.date-range-dropdown')
    .directive('dateRangeDropdown', dateRangeDropdown);

  /** @ngInject */
  function dateRangeDropdown($rootScope, FilterService, WidgetService, AccountsService) {
    return {
      restrict: 'E',
      templateUrl: "/static/assets/js/app/_components/date-range-dropdown/components.date-range-dropdown.directive.html",
      scope: {
        currentDate: '=?',
        isAllOptionsShown: '=',
        onChange: '&'
      },
      link: function (scope, element, attrs) {
        var widget = WidgetService.getCurrent();
        //scope.dateRangeButtons = FilterService.getDateRangeButtons('Past 3 Months');
        scope.btnType = null;
        scope.currentAlias = amplify.store('current_date_alias') || FilterService.getSelectedDateRangeAlias();
        scope.currentDate = amplify.store('current_date_range') || FilterService.getSelectedDateRangeName();
        //scope.isAllOptionsShown  = false;
        scope.cDate = scope.currentDate || FilterService.getSelectedDateRangeName();
        scope.setDateRange = function (range) {
          FilterService.setDateRange(range);
          scope.cDate = FilterService.getSelectedDateRangeName();
          if (scope.currentDate) {
            scope.currentDate = FilterService.getSelectedDateRangeName();
          }
        };
        attrs.$observe('type', function (v) {
          if (v && v == 'compact') {
            scope.btnType = 'btn-sm'
          }
        });
        var acc = null;
        scope.$watch('isAllOptionsShown', function (nVal) {
          if (nVal === true) {
            if (acc && acc.name !== 'BlueSkyAirTrans') {
              scope.dateRangeButtons = FilterService.getDateRangeButtons(['Demo Date Range']);

            }
            else if (acc && acc.name !== 'epicAcc') {
              scope.dateRangeButtons = FilterService.getDateRangeButtons(['Epic Date Range']);
            }
            else {
              scope.dateRangeButtons = FilterService.getDateRangeButtons();
            }
          } else {
            if (acc && acc.name !== 'BlueSkyAirTrans') {
              scope.dateRangeButtons = FilterService.getDateRangeButtons(['Demo Date Range', 'Past 3 Months']);
            } else {
              scope.dateRangeButtons = FilterService.getDateRangeButtons(['Past 3 Months']);
            }
          }
          scope.currentDate = amplify.store('current_date_range') || scope.currentDate;
        });

        // only show Demo Date Range for accounts with name BlueSkyAirTrans
        $rootScope.$on(AccountsService.ACCOUNTS_EVENT, function () {
          acc = AccountsService.getCurrent();
          if (acc.name == 'BlueSkyAirTrans') {
            scope.dateRangeButtons = scope.isAllOptionsShown ? FilterService.getDateRangeButtons() :
              FilterService.getDateRangeButtons(['Past 3 Months']);
          } else {
            scope.dateRangeButtons = scope.isAllOptionsShown ? FilterService.getDateRangeButtons(['Demo Date Range']) :
              FilterService.getDateRangeButtons(['Demo Date Range', 'Past 3 Months']);
          }
        });

        scope.$watch('currentDate', function (newVal, oldVal) {
          if (newVal !== oldVal) {
            scope.cDate = scope.currentDate;
          }
        }, true);

        scope.$watch('cDate', function (newVal, oldVal) {
          //console.log("Try to persist daterange");
          if (newVal !== oldVal || widget) {
            if (FilterService.getSelectedDateRangeAlias() != 'past_3_months') {
              //persist chosen daterange
              // don't store if current url is /dashboard
              if (location.pathname !== "/dashboard") {
                amplify.store('current_date_range',
                  FilterService.getSelectedDateRangeName(),
                  {expires: 86400000});
                amplify.store('current_date_alias',
                  FilterService.getSelectedDateRangeAlias(),
                  {expires: 86400000});
              }
              scope.onChange({dates: FilterService.getDateRange()});
            }
          }
        }, true);

        if (scope.currentAlias && !widget) {
          //console.log("Set DateRange Alias as: " + scope.currentAlias);
          FilterService.setDateRangeByAlias(scope.currentAlias);
        } else if (widget) {
          //console.log("Setting date from widget!");
          FilterService.setDateRange(widget.extra_settings.range_type);
          scope.cDate = FilterService.getSelectedDateRangeName();
        }
      }
    }
  }
})();