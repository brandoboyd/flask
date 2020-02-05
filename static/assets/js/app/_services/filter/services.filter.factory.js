(function () {
  'use strict';

  angular
    .module('slr.services')
    .factory('FilterService', FilterService);

  // TODO: this requires refactoring, in case of some methods are deprecated, or do not make sense, or duplicated
  /**
   * Global filter factory
   * has the same behaviour per each page
   */
  /** @ngInject */
  function FilterService($rootScope, MetadataService) {
    var partial = _.partial,
      allSelected = {
        intentions: true,
        age_groups: true,
        customer_statuses: true,
        agent_occupancy: true,
        message_types: true,
        statuses: true,
        sentiments: true,
        languages: true,
        nps: true,
        journey_status: true
      },

      facetOptions = {
        intentions: MetadataService.getIntentions(),
        age_groups: MetadataService.getAgeGroups(),
        customer_statuses: MetadataService.getCustomerStatuses(),
        agent_occupancy: MetadataService.getAgentOccupancy(),
        statuses: MetadataService.getPostStatuses(),
        sentiments: MetadataService.getSentiments(),
        message_types: MetadataService.getMessageTypes(),
        languages: MetadataService.getLanguages(),
        nps: MetadataService.getNPS(),
        journey_status: MetadataService.getJourneyStatus()
      };

    var dateRangeObj = {
      from: Date.today(),                //(0).days().fromNow(),
      to: Date.today().add({days: 1})                 //(1).days().fromNow()
    };

    var dateRange = {
      from: dateRangeObj.from.toString("MM/dd/yyyy"),
      to: dateRangeObj.to.toString("MM/dd/yyyy")
    };

    // TODO: change "new Date" to momentjs ?
    var today = new Date(dateRangeObj.from),
      this_week_start = Date.mon() <= Date.today() ? Date.mon() : Date.sun().add(-6).days(),
      this_month_start = new Date(dateRangeObj.from).moveToFirstDayOfMonth(),

      tomorrow = new Date(today).add({days: 1}),
      this_week_end = new Date(this_week_start).add({weeks: 1}),
      this_month_end = new Date(this_month_start).add({months: 1}),

      yesterday = new Date(today).add({days: -1}),
      last_week_start = new Date(this_week_start).add({weeks: -1}),
      last_week_end = new Date(last_week_start).add({weeks: 1}),
      last_month_start = new Date(this_month_start).add({months: -1}),
      last_month_end = new Date(last_month_start).add({months: 1}),

      before_last_month_start = new Date(last_month_start).add({months: -1}),
      before_last_month_end = new Date(before_last_month_start).add({months: 1}),

      demo_range_start = before_last_month_start,
      demo_range_end = new Date();

    var monthNames = ["January", "February", "March", "April", "May", "June",
      "July", "August", "September", "October", "November", "December"];
    //the logic behind 'to' the server expects is the end date -1 day
    var dateRangeButtons = [
      //{ alias: 'demo_date_range', type : 'Demo Date Range', from: demo_range_start, to: demo_range_end,  level: 'day', topic_level: 'day', graph_level: 'day', enabled : false },
      {
        alias: 'today',
        type: 'Today',
        from: today,
        to: new Date(today).add({days: 1}),
        level: 'hour',
        topic_level: 'day',
        graph_level: 'hour',
        enabled: true
      },
      {
        alias: 'yesterday',
        type: 'Yesterday',
        from: yesterday,
        to: today,
        level: 'hour',
        topic_level: 'day',
        graph_level: 'hour',
        enabled: false
      },
      {
        alias: 'this_week',
        type: 'This Week',
        from: this_week_start,
        to: this_week_end,
        level: 'day',
        topic_level: 'day',
        graph_level: 'day',
        enabled: false
      },
      {
        alias: 'last_week',
        type: 'Last Week',
        from: last_week_start,
        to: last_week_end,
        level: 'day',
        topic_level: 'day',
        graph_level: 'day',
        enabled: false
      },
      {
        alias: 'this_month',
        type: 'This Month',
        from: this_month_start,
        to: this_month_end,
        level: 'month',
        topic_level: 'month',
        graph_level: 'day',
        enabled: false
      },
      {
        alias: 'last_month',
        type: monthNames[last_month_start.getMonth()],
        from: last_month_start,
        to: last_month_end,
        level: 'month',
        topic_level: 'month',
        graph_level: 'day',
        enabled: false
      },
      {
        alias: 'before_last_month',
        type: monthNames[before_last_month_start.getMonth()],
        from: before_last_month_start,
        to: before_last_month_end,
        level: 'month',
        topic_level: 'month',
        graph_level: 'day',
        enabled: false
      },
      {
        alias: 'past_3_months',
        type: 'Past 3 Months',
        from: new Date(this_month_start).add({months: -2}),
        to: today,
        level: 'month',
        topic_level: 'month',
        graph_level: 'day',
        enabled: false
      },
      {
        alias: 'past_3_year',
        type: 'Past 3 years',
        from: new Date(this_month_start).add({years: -3}),
        to: today,
        level: 'month',
        topic_level: 'month',
        graph_level: 'day',
        enabled: false
      }
    ];

    /* Private methods */

    var getSelected = function (list, label) {
      var field = label ? label : 'label';
      return _.pluck(_.filter(list,
        function (el) {
          return el.enabled == true
        }
      ), field);
    };

    var getEnabled = function (list) {
      return _.filter(list, function (el) {
        return el.enabled == true
      });
    };

    var setFacetFilters = function (selected, all, event) {
      _.each(all, function (el) {
        if (selected.length > 0)
          el.enabled = _.some(selected, function (sel) {
            return sel == el.label
          });
        else
          el.enabled = false
      });
      $rootScope.$broadcast(event);
      return all;
    };

    var removeSelectedFilter = function (filter, facet, event, field) {
      field = field ? field : 'label';
      var removed = _.find(facet, function (el) {
        return el[field] == filter
      });
      if (removed)
        removed.enabled = false;
      $rootScope.$broadcast(event);
    };

    var getFacetParams = function (facet) {
      var isAll = isAllSelected(facet),
        options = getFacetOptions(facet);
      if (isAll) {
        return _.pluck(options, 'label');
      } else {
        return getSelected(options);
      }
    };

    /* End of Private methods */
    var LANGUAGES = 'languages',
      INTENTIONS = 'intentions',
      AGE_GROUPS = 'age_groups',
      CUSTOMER_STATUSES = 'customer_statuses',
      AGENT_OCCUPANCY = 'agent_occupancy',
      SENTIMENTS = 'sentiments',
      STATUSES = 'statuses',
      MESSAGE_TYPES = 'message_types',
      NPS = 'nps',
      JOURNEY_STATUS = 'journey_status';

    var FilterService = {
      CHANGED: 'filter_changed',
      DATE_RANGE_CHANGED: 'date_range_changed',
      INTENTIONS_CHANGED: 'intentions_changed',
      AGE_GROUPS_CHANGED: 'age_groups_changed',
      CUSTOMER_STATUSES_CHANGED: 'customer_statuses_changed',
      AGENT_OCCUPANCY_CHANGED: 'agent_occupancy_changed',
      MESSAGE_TYPE_CHANGED: 'message_type_changed',
      POST_STATUSES_CHANGED: 'post_statuses_changed',
      SENTIMENTS_CHANGED: 'sentiments_changed',
      LANGUAGES_CHANGED: 'languages_changed',

      setSelectedIntentions: partial(setSelected, INTENTIONS),
      //setSelectedAgeGroups      : partial(setSelected, AGE_GROUPS),
      setSelectedLanguages: partial(setSelected, LANGUAGES),
      setSelectedSentiments: partial(setSelected, SENTIMENTS),
      setSelectedStatuses: partial(setSelected, STATUSES),
      setDateRange: setDateRange,
      setDateRangeByAlias: setDateRangeByAlias,
      getUTCDate: getUTCDate,
      getDateRangeButtons: getDateRangeButtons,
      getDateRange: getDateRange,
      update: update,
      updateDateRange: updateDateRange,
      getDateRangeObj: getDateRangeObj,
      getSelectedDateRangeType: getSelectedDateRangeType,
      getSelectedDateRangeAlias: getSelectedDateRangeAlias,
      getDateRangeByAlias: getDateRangeByAlias,
      getSelectedDateRangeName: getSelectedDateRangeName,
      getSelectedLevel: getSelectedLevel,
      getSelectedGraphLevel: getSelectedGraphLevel,
      getSelectedTopicLevel: getSelectedTopicLevel,
      toUTCDate: toUTCDate,
      getPostsDateRangeByPoint: getPostsDateRangeByPoint,
      getMessageTypes: partial(getFacetOptions, MESSAGE_TYPES),
      getIntentions: partial(getFacetOptions, INTENTIONS),
      getAgeGroups: partial(getFacetOptions, AGE_GROUPS),
      getCustomerStatuses: partial(getFacetOptions, CUSTOMER_STATUSES),
      getAgentOccupancy: partial(getFacetOptions, AGENT_OCCUPANCY),
      getNPSOptions: partial(getFacetOptions, NPS),
      getJourneyStatus: partial(getFacetOptions, JOURNEY_STATUS),
      getSentiments: partial(getFacetOptions, SENTIMENTS),
      isAllSelected: isAllSelected,
      facetsAllSelected: facetsAllSelected,
      isAllIntentionsSelected: partial(isAllSelected, INTENTIONS),
      //isAllAgeGroupsSelected    : partial(isAllSelected, AGE_GROUPS),
      isAllMessageTypesSelected: partial(isAllSelected, MESSAGE_TYPES),
      isAllStatusesSelected: partial(isAllSelected, STATUSES),
      isAllSentimentsSelected: partial(isAllSelected, SENTIMENTS),
      isAllLanguagesSelected: partial(isAllSelected, LANGUAGES),
      setIntentions: partial(setFacetFiltersCur, INTENTIONS),
      setAgeGroups: partial(setFacetFiltersCur, AGE_GROUPS),
      setCustomerStatuses: partial(setFacetFiltersCur, CUSTOMER_STATUSES),
      setAgentOccupancy: partial(setFacetFiltersCur, AGENT_OCCUPANCY),
      setMessageTypes: partial(setFacetFiltersCur, MESSAGE_TYPES),
      setStatuses: partial(setFacetFiltersCur, STATUSES),
      setSentiments: partial(setFacetFiltersCur, SENTIMENTS),
      updatePostStatuses: partial(updateEvent, STATUSES),
      updateIntentions: partial(updateEvent, INTENTIONS),
      updateAgeGroups: partial(updateEvent, AGE_GROUPS),
      updateCustomerStatuses: partial(updateEvent, CUSTOMER_STATUSES),
      updateAgentOccupancy: partial(updateEvent, AGENT_OCCUPANCY),
      updateMessageTypes: partial(updateEvent, MESSAGE_TYPES),
      updateSentiments: partial(updateEvent, SENTIMENTS),
      setIsAllMessageTypes: partial(setIsAll, MESSAGE_TYPES),
      setIsAllIntentions: partial(setIsAll, INTENTIONS),
      setIsAllAgeGroups: partial(setIsAll, AGE_GROUPS),
      setIsAllCustomerStatuses: partial(setIsAll, CUSTOMER_STATUSES),
      setIsAllAgentOccupancy: partial(setIsAll, AGENT_OCCUPANCY),
      setIsAllStatuses: partial(setIsAll, STATUSES),
      setIsAllSentiments: partial(setIsAll, SENTIMENTS),
      setIsAllLanguages: partial(setIsAll, LANGUAGES),
      removeIntention: removeIntention,
      removeAgeGroup: removeAgeGroup,
      removeCustomerStatus: removeCustomerStatus,
      removeAgentOccupancy: removeAgentOccupancy,
      removeStatus: removeStatus,
      removeSentiment: removeSentiment,
      getPostStatuses: partial(getFacetOptions, STATUSES),
      getSelectedMessageTypes: partial(getSelectedCur, MESSAGE_TYPES, 'display'),
      getSelectedIntentions: partial(getSelectedCur, INTENTIONS, 'display'),
      getSelectedAgeGroups: partial(getSelectedCur, AGE_GROUPS, 'display'),
      getSelectedCustomerStatuses: partial(getSelectedCur, CUSTOMER_STATUSES, 'display'),
      getSelectedAgentOccupancy: partial(getSelectedCur, AGENT_OCCUPANCY, 'display'),
      getSelectedSentiments: partial(getSelectedCur, SENTIMENTS),
      getMessageTypesParams: partial(getFacetParams, MESSAGE_TYPES),
      getLanguagesParams: partial(getFacetParams, LANGUAGES),
      getIntentionsParams: partial(getFacetParams, INTENTIONS),
      getAgeGroupsParams: partial(getFacetParams, AGE_GROUPS),
      getCustomerStatusesParams: partial(getFacetParams, CUSTOMER_STATUSES),
      getAgentOccupancyParams: partial(getFacetParams, AGENT_OCCUPANCY),
      getSentimentsParams: partial(getFacetParams, SENTIMENTS),
      getSelectedPostStatuses: getSelectedPostStatuses,
      getPostStatusesParams: partial(getFacetParams, STATUSES),
      initLanguages: initLanguages,
      getLanguages: partial(getFacetOptions, LANGUAGES),
      setLanguages: partial(setFacetFiltersCur, LANGUAGES),
      updateLanguages: partial(updateEvent, LANGUAGES),
      getSelectedLanguages: partial(getSelectedCur, LANGUAGES, 'title'),
      removeLanguage: removeLanguage
    };
    return FilterService;

    /* Public Methods (exposed via FilterService object) - use function declaration to hoist them */

    function setSelected(facet, labels) {
      var options = getFacetOptions(facet);
      _.each(options, function (el) {
        el.enabled = false;
        _.each(labels, function (label) {
          if (label == el.label) {
            el.enabled = true;
          }
        })
      });

      updateEvent(facet);
    }

    function setDateRange(range) {
      angular.forEach(dateRangeButtons, function (val, key) {
        if (val.type === range) {
          val.enabled = true;
          dateRangeObj.to = val.to;
          dateRangeObj.from = val.from;
          //console.log(dateRangeButtons);
        } else {
          val.enabled = false;
        }
      });
      updateDateRange(dateRangeObj);
      $rootScope.$broadcast(FilterService.DATE_RANGE_CHANGED);
    }

    function setDateRangeByAlias(alias) {
      var selected = getDateRangeByAlias(alias);
      setDateRange(selected.type);
    }

    function getUTCDate(date) {
      return new Date(date.getUTCFullYear(),
        date.getUTCMonth(),
        date.getUTCDate(),
        date.getUTCHours(),
        date.getUTCMinutes(),
        date.getUTCSeconds());
    }

    function update(obj) {
      $rootScope.$broadcast(FilterService.CHANGED, obj);
    }

    function getDateRangeButtons(types) {
      var ids = {};
      _.each(types, function (type) {
        ids[type] = true;
      });
      var filteredDRbuttons = _.filter(dateRangeButtons, function (val) {
        return !ids[val.type];
      }, types);
      //console.log(filteredDRbuttons);
      return filteredDRbuttons;
    }

    function getDateRange(params) {
      var storedAllias = amplify.store('current_date_alias') || getSelectedDateRangeAlias();
      var datesByAlias = getDateRangeByAlias(storedAllias);
      //dateRange.from = (datesByAlias.from).toString("MM/dd/yyyy");
      //dateRange.to   = (datesByAlias.to).toString("MM/dd/yyyy");
      if (params && params.local) {
        // treat dateRange as local, and covert to UTC equivalent before sending request to server
        // useful when server can handle 'any'date range query (unlike aggregated posts data page which needs UTC days),
        // and UI (eg: setting pages) will format the dates in local timezone
        dateRange.from = moment.utc(dateRange.from).format('YYYY-MM-DD HH:mm:SS');
        dateRange.to = moment.utc(dateRange.to).format('YYYY-MM-DD HH:mm:SS');
      }
      return dateRange;
    }

    function updateDateRange(dates) {
      dateRangeObj = dates;
      dateRange.from = new Date(dates.from).toString("MM/dd/yyyy");
      dateRange.to = new Date(dates.to).toString("MM/dd/yyyy");

      angular.forEach(dateRangeButtons, function (val, key) {
        if (new Date(val.from).toString('MM/dd/yyyy') === dateRange.from &&
          new Date(val.to).toString('MM/dd/yyyy') === dateRange.to) {
          val.enabled = true;
        } else {
          val.enabled = false;
        }
      });
      $rootScope.$broadcast(FilterService.DATE_RANGE_CHANGED);
    }

    function getDateRangeObj() {
      return dateRangeObj;
    }

    function getSelectedDateRangeType() {
      return getEnabled(getDateRangeButtons())[0].type;
    }

    function getSelectedDateRangeAlias() {
      return getEnabled(getDateRangeButtons())[0].alias;
    }

    function getDateRangeByAlias(alias) {
      return _.find(dateRangeButtons, function (btn) {
        return btn.alias == alias
      })
    }

    function getSelectedDateRangeName() {
      var date = getEnabled(getDateRangeButtons())[0];
      var from = dateFormat(date.from, "mmm dd");
      var to = dateFormat(date.to, "mmm dd");
      var range = from + " - " + to;
      return range;
    }

    function getSelectedLevel() {
      return getEnabled(getDateRangeButtons())[0]['level'];
    }

    function getSelectedGraphLevel() {
      return getEnabled(getDateRangeButtons())[0]['graph_level'];
    }

    function getSelectedTopicLevel() {
      return getEnabled(getDateRangeButtons())[0]['topic_level'];
    }

    function toUTCDate(date, format) {
      var _date = new Date(date);
      var timestamp = Date.UTC(_date.getFullYear(), _date.getMonth(), _date.getDate());
      var local_date = new Date(timestamp);
      return format ? dateFormat(local_date, "yyyy-mm-dd HH:MM:ss", true) : timestamp;
    }

    function getPostsDateRangeByPoint(timePoint, plot_by, level) {
      level = level ? level : getSelectedLevel();
      var fromDate = new Date(timePoint),
        toDate;
      if (plot_by == 'time') {
        if (level == 'hour') {
          toDate = new Date(fromDate).add({hours: 1});
        } else if (level == 'day' || level == 'month') {
          fromDate = new Date(fromDate);
          toDate = new Date(fromDate).add({days: 1});
        }
      }
      toDate.add({seconds: -1});
      return {from: fromDate, to: toDate};
    }

    function ensureFacetIn(facet, obj) {
      if (!obj.hasOwnProperty(facet)) {
        throw Error("Unknown facet: " + facet);
      }
    }

    function isAllSelected(facet) {
      ensureFacetIn(facet, allSelected);
      return allSelected[facet];
    }

    function facetsAllSelected() {
      var res = [];
      for (var facet in allSelected) {
        if (allSelected.hasOwnProperty(facet) && allSelected[facet] === true) {
          res.push(facet);
        }
      }
      return res;
    }

    function setIsAll(facet, selected) {
      ensureFacetIn(facet, allSelected);
      allSelected[facet] = selected;
    }

    function getFacetOptions(facet) {
      ensureFacetIn(facet, facetOptions);
      var options = facetOptions[facet];
      if (facet == LANGUAGES || facet == STATUSES) {
        return options;
      } else {
        return _.sortBy(options, function (el) {
          return el.label;
        });
      }
    }

    function getEvent(facet) {
      var events = {
        intentions: FilterService.INTENTIONS_CHANGED,
        age_groups: FilterService.AGE_GROUPS_CHANGED,
        customer_statuses: FilterService.CUSTOMER_STATUSES_CHANGED,
        agent_occupancy: FilterService.AGENT_OCCUPANCY_CHANGED,
        message_types: FilterService.MESSAGE_TYPE_CHANGED,
        statuses: FilterService.POST_STATUSES_CHANGED,
        sentiments: FilterService.SENTIMENTS_CHANGED,
        languages: FilterService.LANGUAGES_CHANGED
      };
      return events[facet];
    }

    function setFacetFiltersCur(facet, list) {
      var all = getFacetOptions(facet),
        event = getEvent(facet);
      return setFacetFilters(list, all, event);
    }


    function updateEvent(facet) {
      var event = getEvent(facet);
      $rootScope.$broadcast(event);
    }

    function removeIntention(item) {
      removeSelectedFilter(item, FilterService.getIntentions(), FilterService.INTENTIONS_CHANGED, 'display');
    }

    function removeAgeGroup(item) {
      removeSelectedFilter(item, FilterService.getAgeGroups(), FilterService.AGE_GROUPS_CHANGED, 'display');
    }

    function removeCustomerStatus(item) {
      removeSelectedFilter(item, FilterService.getCustomerStatuses(), FilterService.CUSTOMER_STATUSES_CHANGED, 'display');
    }

    function removeAgentOccupancy(item) {
      removeSelectedFilter(item, FilterService.getAgentOccupancy(), FilterService.AGENT_OCCUPANCY_CHANGED, 'display');
    }

    function removeStatus(item) {
      //removeSelectedFilter(item, getPostStatuses(), POST_STATUSES_CHANGED);
      var removed = _.find(FilterService.getPostStatuses(), function (el) {
        //return el.label == item
        return el.display == item.display
      });
      if (removed)
        removed.enabled = false;
      $rootScope.$broadcast(FilterService.POST_STATUSES_CHANGED);
    }

    function removeSentiment(item) {
      removeSelectedFilter(item, FilterService.getSentiments(), FilterService.SENTIMENTS_CHANGED);
    }

    function getSelectedCur(facet, label) {
      var all = getFacetOptions(facet);
      return getSelected(all, label);
    }

    function getSelectedPostStatuses(returnItems) {
      var wrapper = returnItems ? getEnabled : getSelected;
      return wrapper(getFacetOptions(STATUSES));
    }

    function initLanguages(langs) {
      var languages = _.each(langs,
        function (el) {
          return _.defaults(el, {enabled: false, label: el.title});
        });
      facetOptions.languages = languages;
      return languages;
    }

    function removeLanguage(item) {
      removeSelectedFilter(item, FilterService.getLanguages(), FilterService.LANGUAGES_CHANGED, 'title');
    }
  }
})();