xdescribe('Analysis Panel', function () {
  var compile, scope, element, vm;

  beforeEach(module("slr.analysis"));
  beforeEach(module(function ($provide) {
    $provide.value('SystemAlert');
  }));

  beforeEach(inject(function ($rootScope, $compile) {
    scope = $rootScope.$new();
    compile = $compile;

    element = angular.element('<div analysis-panel analysis-filters="{{filters}}"' +
                                  ' analysis-extra-params="{{metrics}}"></div>');
    scope.filters = {};
    scope.metrics = {metrics: ['csat_score']};

    compile(element)(scope);
    scope.$digest();
    vm = element.isolateScope();
  }));

  it('should render analysis panel', function () {
    expect(element.html()).not.toEqual(null);
    console.log(element.html());
  });
});