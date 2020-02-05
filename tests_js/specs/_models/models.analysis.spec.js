describe('AnalysisRest', function () {
  var ModelRest;
  var AnalysisRest;
  var report;
  var $httpBackend;

  var testReport = {
    id: "5731281b3de8ff157d9d1fa7",
    title: "Test Report",
    status: 'active'
  };
  var URLs = {
    list: '/analyzers',
    one: '/analyzers/' + testReport.id
  };

  beforeEach(angular.mock.module("slr.models"));

  beforeEach(angular.mock.inject(function (_ModelRest_, _AnalysisRest_, _$httpBackend_) {
    ModelRest = _ModelRest_;
    AnalysisRest = new _AnalysisRest_();
    $httpBackend = _$httpBackend_;
  }));

  it('should get the list of analysis reports', function (done) {
    AnalysisRest.list()
      .success(function (res) {
        expect(res.list.length).toBeGreaterThan(0);
        report = res.list[0];
        done();
      })
      .error(catchFail(done));

    $httpBackend.when('GET', URLs.list).respond(200, {
      list: [testReport]
    });
    $httpBackend.flush();
  });

  it('should get one report', function (done) {
    AnalysisRest.getOne(report.id)
      .success(function (res) {
        expect(res.item).toEqual(report);
        done();
      })
      .error(catchFail(done));

    $httpBackend.when('GET', URLs.one).respond(200, {
      item: testReport
    });
    $httpBackend.flush();
  });

  it('should run report', function (done) {
    report.title = 'Wu Tang Report';
    AnalysisRest.run(report)
      .success(function (res) {
        expect(res.item.title).toBe(report.title);
        done();
      })
      .error(catchFail(done));

    $httpBackend.when('POST', URLs.list, report).respond({
      item: report
    });
    $httpBackend.flush();
  });

  it('should stop report', function (done) {
    AnalysisRest.stop(report.id)
      .success(function () {
        expect(report.status).toBe('stopped');
        done();
      })
      .error(catchFail(done));

    $httpBackend.when('POST', URLs.one + '/stop').respond(function () {
      report.status = 'stopped';
      return [200, report];
    });
    $httpBackend.flush();
  });

  it('should remove report', function (done) {
    AnalysisRest.remove(report.id)
      .success(function () {
        expect(report).toEqual({});
        done();
      })
      .error(catchFail(done));

    $httpBackend.when('DELETE', URLs.one).respond(function () {
      report = {};
      return [200, report];
    });
    $httpBackend.flush();
  });

});