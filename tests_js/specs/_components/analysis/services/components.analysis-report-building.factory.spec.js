describe('Analysis Report Factory', function () {
  var AnalysisReport;
  var data;
  var Utils;
  var ModelRest;
  var AnalysisRest;
  var $httpBackend;

  beforeEach(angular.mock.module("slr.components"));
  beforeEach(angular.mock.module("slr.analysis"));
  beforeEach(angular.mock.module("slr.models"));
  beforeEach(angular.mock.module("tests_js_factory"));

  beforeEach(angular.mock.inject(function (_AnalysisReport_, _Utils_, _ModelRest_, _AnalysisRest_, _$httpBackend_, _TestsFactory_) {
    AnalysisReport = _AnalysisReport_;
    Utils = _Utils_;
    ModelRest = _ModelRest_;
    AnalysisRest = new _AnalysisRest_();
    $httpBackend = _$httpBackend_;

    data = _TestsFactory_.getAnalysisMockRegressionData();
  }));

  it('buildReport', function () {
    AnalysisReport.buildReport(data.report, function (res) {
      expect(res).toBeDefined();

      var validResponseKeys = ['report', 'metricData', 'tabs'];
      var validReportKeys = ['analysis_type', 'analyzed_metric', 'metric_type',
        'metric_values', 'metric_values_range', 'id',
        'timerange_results', 'title', 'parsedFilters',
        'parsedResults', 'parsed_analyzed_metric', 'width', 'tabs'];

      expect(_.every(validResponseKeys, function (k) { return _.has(res, k); })).toBeTruthy();
      expect(_.every(validReportKeys, function (k) { return _.has(res.report, k); })).toBeTruthy();
    });
  });

  it('should return properly parsed facets in parsedFilters', function () {
    _.extend(data.report, {
      filters: {
        facets: {nps: [9, 10]}
      }
    });
    AnalysisReport.buildReport(data.report, function (res) {
      expect(res).toBeDefined();
      expect(_.has(res.report, 'dynFacets')).toBeTruthy();
    });
  });

  it('deleteReport', function (done) {
    AnalysisRest.remove(data.report.id)
      .success(done)
      .error(catchFail(done));

    $httpBackend.when('DELETE', ['/analyzers', data.report.id].join('/')).respond(200, {
      ok: true
    });
    $httpBackend.flush();
  });

  xit('paginate', function () {
  });

  xit('getParsedSemantics', function () {
  });

  xit('disableFlags', function () {
  });

  xit('getParsedJourneyFilters', function () {
  });

  xit('getParsedPredictorFilters', function () {
  });

  xit('exportTable', function () {
  });

  xit('selectFeature', function () {
  });

});