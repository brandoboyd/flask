xdescribe('Chart Directive', function () {
  var compile, scope, element, vm;

  beforeEach(module("slr.components"));
  beforeEach(module("slr.chart"));
  beforeEach(module(function ($provide) {
    $provide.value('SystemAlert');
  }));

  beforeEach(inject(function ($rootScope, $compile) {
    scope = $rootScope.$new();
    compile = $compile;

    element = angular.element('<chart chart-data=\'{{data}}\' settings=\'{{extra_settings}}\'></chart>');

    scope.data = {};
    scope.extra_settings = {};

    compile(element)(scope);
    scope.$digest();
    vm = element.isolateScope();
  }));

  it('should render chart', function () {
    expect(element.html()).not.toEqual(null);
  });
});