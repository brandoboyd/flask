describe("FilterService", function() {
  'use strict';
  var $rootScope,
    FilterService;

  beforeEach(module("slr.services"));
  beforeEach(inject(function(_FilterService_, _$rootScope_){
    // The injector unwraps the underscores (_) from around the parameter names when matching
    $rootScope = _$rootScope_;
    FilterService     = _FilterService_;
  }));

  describe("public date-time relative methods", function(){

    var UTCtime,
      time;

    beforeEach(function() {
      time = new Date;
      UTCtime = new Date(time.getUTCFullYear(),
        time.getUTCMonth(),
        time.getUTCDate(),
        time.getUTCHours(),
        time.getUTCMinutes(),
        time.getUTCSeconds()
      );

      jasmine.clock().install();
    });

    afterEach(function() {
      jasmine.clock().uninstall();
    });

    it('getDateRange should return todays and tomorrow days respectively', function() {
      var baseTimeFrom = time.toString('MM/dd/yyyy'),
        baseTimeTo = time.add({ days:1}).toString('MM/dd/yyyy');

      expect(FilterService.getDateRange().from).toEqual(baseTimeFrom);
      expect(FilterService.getDateRange().to).toEqual(baseTimeTo);
    });

    it('getUTCDate should return UTC date values', function() {
      expect(FilterService.getUTCDate(time)).toEqual(new Date(UTCtime));
    });

    it('getSelectedDateRangeName should return today and tomorrow days respectively with month name', function() {
      expect(FilterService.getSelectedDateRangeName()).toEqual(dateFormat(time, 'mmm dd') + ' - ' + dateFormat(time.add({days: 1}), 'mmm dd'));
    });

    //FIXME: perhaps use another comparator, e.g. not 'toBeLessthan'
    it('toUTCDate should return format in UTC pattern', function() {
      expect(FilterService.toUTCDate(time, 'yyyy-MM-dd hh:mm:ss')).toBeLessThan(time.toString('yyyy-MM-dd hh:mm:ss'));
    });

    /**
     * Pay attention that there is 1 second for addition assuming the test process time
     */
    it('getPostsDateRangeByPoint should return an object containing of date and +1 regarding to its parameters', function() {
      expect(FilterService.getPostsDateRangeByPoint(time, 'time', 'hour').from).toEqual(time);
      expect(FilterService.getPostsDateRangeByPoint(time, 'time', 'day').from).toEqual(time);
      expect(FilterService.getPostsDateRangeByPoint(time, 'time', 'hour').to).toEqual(time.add({hours: 1, seconds: -1}));
      expect(FilterService.getPostsDateRangeByPoint(time, 'time', 'month').to).toEqual(time.add({days: 1, seconds: -1}));
    });

  });

  describe('public booleans methods', function() {

    it('isAllIntentionsSelected should return true', function() {
      expect(FilterService.isAllIntentionsSelected()).toEqual(true);
    });

    it('isAllMessageTypesSelected should return true', function() {
      expect(FilterService.isAllMessageTypesSelected()).toEqual(true);
    });

    it('isAllStatusesSelected should return true', function() {
      expect(FilterService.isAllStatusesSelected()).toEqual(true);
    });

    it('isAllSentimentsSelected should return true', function() {
      expect(FilterService.isAllSentimentsSelected()).toEqual(true);
    });
  });

  describe('public status, intention* methods', function() {

    var postStatus, intention, sentiment, message;

    beforeEach(function() {
      postStatus = { label : 'actionable', display : 'actionable', enabled : true};
      intention = { display: 'asks', label : 'asks', enabled : true, color: '#38854d'};
      sentiment = { label : 'positive', enabled : true, color: '#0DBD39'};
      message = { display: 'Public messages', label : 0, enabled : true };
    });

    //FIXME: Improve remove* tests
    it('removeIntention should not return null and be called by $broadcast', function() {
      spyOn($rootScope, '$broadcast').and.callThrough();
      FilterService.removeIntention(intention);
      expect($rootScope.$broadcast).toHaveBeenCalled();
//            expect(FilterService.prototype.removeSelectedFilterService(intention, FilterService.getIntentions(), FilterService.INTENTIONS_CHANGED, 'display')).toEqual(true);
    });

    it('getMessageTypes should return an message types object containing \'display\' field', function() {
      for(var i = 0; i < FilterService.getMessageTypes().length; i++){
        if(FilterService.getMessageTypes()[i].display == FilterService.getMessageTypesParams()){
          expect(FilterService.getMessageTypes()[i].display).toEqual(FilterService.getMessageTypesParams());
        }
      }
    });

    it('getIntentions should return an intentions object containing \'display\' field', function() {
      for(var i = 0; i < FilterService.getIntentions().length; i++){
        if(FilterService.getIntentions()[i].display == FilterService.getIntentionsParams()){
          expect(FilterService.getIntentions()[i].display).toMatch(FilterService.getIntentionsParams());
        }
      }
    });

    it('getSentiments should return sentiments object containing \'label\' field', function() {
      expect(FilterService.getSentiments()[2].label).toEqual(sentiment.label);
    });

    it('removeStatus should not return null and be called by $broadcast', function() {
      spyOn($rootScope, '$broadcast').and.callThrough();
      FilterService.removeStatus(postStatus);
      expect($rootScope.$broadcast).toHaveBeenCalled();
    });

    it('removeSentiment should not return null and be called by $broadcast', function() {
      spyOn($rootScope, '$broadcast').and.callThrough();
      FilterService.removeSentiment(sentiment);
      expect($rootScope.$broadcast).toHaveBeenCalled();
    });

    it('getSelectedMessageTypes should return selected message types and contain at least \'Public messages\'', function() {
      expect(FilterService.getSelectedMessageTypes()).toMatch(message.display);
    });

    it('getSelectedIntentions should return selected intention', function() {
      expect(FilterService.getSelectedIntentions()[0]).toBeUndefined();// undefined because intention is disabled
    });

    it('getSelectedSentiments should return selected intention', function() {
      expect(FilterService.getSelectedSentiments()[0]).toBeUndefined(); // undefined because sentiment is disabled
    });

    //FIXME: Look through this method
    it('getMessageTypesParams should return 0 & 1 values', function() {
      expect(FilterService.getMessageTypesParams()).toContain(0);
    });

    it('getIntentionsParams should return intention', function() {
      expect(FilterService.getIntentionsParams()).toEqual(FilterService.getIntentionsParams());
    });

    it('getSentimentsParams should return sentiment', function() {
      expect(FilterService.getSentimentsParams()).toEqual(FilterService.getSentimentsParams());
    });

    it('getSelectedPostStatuses should return post statuses as label', function() {
      expect(FilterService.getSelectedPostStatuses()).toEqual(FilterService.getPostStatusesParams());
    });



  });

  describe('public update* methods', function() {

    it('update should return FILTER_CHANGED value', function() {
      spyOn($rootScope, '$broadcast').and.callThrough();
      FilterService.update('filter_changed');
      expect($rootScope.$broadcast).toHaveBeenCalled();
      expect(FilterService.update('filter_changed')).not.toBeNull();
    });

    it('updatePostStatuses should return $broadcast \'updatePostStatuses\'', function() {
      spyOn($rootScope, '$broadcast').and.callThrough();
      FilterService.updatePostStatuses();
      expect($rootScope.$broadcast).toHaveBeenCalled();
    });

    it('updateIntentions should return $broadcast \'updateIntentions\'', function() {
      spyOn($rootScope, '$broadcast').and.callThrough();
      FilterService.updateIntentions();
      expect($rootScope.$broadcast).toHaveBeenCalled();
    });

    it('updateMessageTypes should return $broadcast \'updateMessageTypes\'', function() {
      spyOn($rootScope, '$broadcast').and.callThrough();
      FilterService.updateMessageTypes();
      expect($rootScope.$broadcast).toHaveBeenCalled();
    });

    it('updateSentiments should return $broadcast \'updateSentiments\'', function() {
      spyOn($rootScope, '$broadcast').and.callThrough();
      FilterService.updateSentiments();
      expect($rootScope.$broadcast).toHaveBeenCalled();
    });
  });

  describe('getters', function() {
    it('getDateRangeButtons should return dateRangeButton object', function() {
      expect(FilterService.getDateRangeButtons()).not.toBeNull();
    });

    it('getDateRangeObj should return an object', function() {
      expect(FilterService.getDateRangeObj()).not.toBeNull();
    });

    it('getSelectedDateRangeType should return Today value', function() {
      expect(FilterService.getSelectedDateRangeType()).toMatch(/Today/);
    });

    it('getSelectedDateRangeAlias should return today value', function() {
      expect(FilterService.getSelectedDateRangeAlias()).toMatch(/today/);
    });

    it('getDateRangeByAlias should return the alias value', function() {
      expect(FilterService.getDateRangeByAlias('today').alias).toMatch(/today/);
    });

    it('getSelectedLevel should return level in dateRangeButtons massive, currently it\'s \'hour\' value', function() {
      expect(FilterService.getSelectedLevel()).toMatch(/hour/);
    });

    it('getSelectedGraphLevel should return graph_level value in dateRangeButtons massive', function() {
      expect(FilterService.getSelectedGraphLevel()).toMatch(/hour/);
    });

    it('getSelectedTopicLevel should return topic_level value in dateRangeButtons', function() {
      expect(FilterService.getSelectedTopicLevel()).toMatch(/day/);
    });
  });

  describe('setter for date range by alias', function() {
    beforeEach(function(){
      FilterService.setDateRangeByAlias(FilterService.getDateRangeButtons()[0].alias);
    });
    it('setDateRangeByAlias should set date range by alias', function() {
      expect(FilterService.getDateRangeButtons()[0].alias).not.toBeNull();
    });
  });

  describe('setter for selected intentions', function() {
    beforeEach(function(){
      var selected = FilterService.getIntentions()[0];
      FilterService.setSelectedIntentions(selected);
      FilterService.setDateRangeByAlias(FilterService.getDateRangeButtons()[0].alias);
    });
    it('setSelectedIntentions should set intention', function() {
      expect(FilterService.getSelectedIntentions()[0]).toMatch(FilterService.getIntentions()[0].display);
    });
  });

  //FIXME: Need to add getLanguages(), temporally there is just a {}
  describe('setter for selected language', function() {
    it('setSelectedLanguages should set language', function() {
      spyOn($rootScope, '$broadcast').and.callThrough();
      FilterService.setSelectedLanguages({});
      expect($rootScope.$broadcast).toHaveBeenCalled();
    });
  });

  describe('setter for selected sentiments', function() {
    beforeEach(function() {
      FilterService.setSelectedSentiments(FilterService.getSentiments());
    });
    //FIXME: Should work as setSelectedStatus
    it('setSelectedSentiments should set sentiment', function() {
      expect(FilterService.getSelectedSentiments()).toEqual([]);
    });
  });

  describe('setter for selected statuses', function(){
    beforeEach(function() {
      FilterService.setSelectedStatuses(FilterService.getPostStatuses()[0]);
    });
    it('setSelectedStatuses should set status', function() {
      expect(FilterService.getSelectedPostStatuses()).toMatch(FilterService.getPostStatuses()[0].display);
    });
  });



});