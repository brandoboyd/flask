xdescribe('Horizontal timeline Directive', function () {
  var compile, scope, element, vm;

  beforeEach(module("slr.components"));
  beforeEach(module("slr.horizontal-timeline"));
  beforeEach(module(function ($provide) {
    $provide.value('SystemAlert');
  }));

  beforeEach(inject(function ($rootScope, $compile) {
    scope = $rootScope.$new();
    compile = $compile;

    element = angular.element('<horizontal-timeline source="horizontalTimeline"'+
                                   'height="180"'+
                                   'width="95%"'+
                                   'start-zoom-adjust="{{zoomAdjust}}"'+
                                   'start-at-end="true"'+
                                   'start-at-slide="{{startAt}}"'+
                                   'hash-bookmark="false"'+
                                   'lang="en"'+
                                   'debug="false"'+
                                   'ng-hide="flags.showErrMsg"'+
                                   'ng-if="horizontalTimeline"'+
                                   'day-events="horizontalTimeline.timeline.date"'+
                                   'show-data="showData(index)"></horizontal-timeline>');
    
    scope.horizontalTimeline = {};
    scope.zoomAdjust = {};
    scope.startAt = {};
    scope.flags = {showErrMsg: false};
    scope.showData = function(index) {};

    compile(element)(scope);
    scope.$digest();
    vm = element.isolateScope();
  }));

  it('should render chart', function () {
    expect(element.html()).not.toEqual(null);
  });
});