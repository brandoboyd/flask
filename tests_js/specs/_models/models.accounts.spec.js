describe('AccountsRest', function () {
  var ModelRest;
  var AccountsRest;
  var account;
  var $httpBackend;

  var testAccount = {
    id: "5731281b3de8ff157d9d1fa7",
    name: "Test Account"
  };
  var URLs = {
    list: '/accounts/json',
    one: '/accounts/' + testAccount.id + '/json'
  };

  beforeEach(angular.mock.module("slr.models"));

  beforeEach(angular.mock.inject(function (_ModelRest_, _AccountsRest_, _$httpBackend_) {
    ModelRest = _ModelRest_;
    AccountsRest = new _AccountsRest_();
    $httpBackend = _$httpBackend_;
  }));

  it('should get the list of accounts', function (done) {
    AccountsRest.list()
      .success(function (res) {
        expect(res.data.length).toBeGreaterThan(0);
        account = res.data[0];
        done();
      })
      .error(catchFail(done));

    $httpBackend.when('GET', URLs.list).respond(200, {
      data: [testAccount]
    });
    $httpBackend.flush();
  });

  it('should get one account', function (done) {
    AccountsRest.getOne(account.id)
      .success(function (res) {
        expect(res.account).toEqual(account);
        done();
      })
      .error(catchFail(done));

    $httpBackend.when('GET', URLs.one).respond(200, {
      account: testAccount
    });
    $httpBackend.flush();
  });

  it('should update account', function (done) {
    account.name = 'Wu Tang';
    AccountsRest.update(account.id, account)
      .success(function (res) {
        expect(res.account.name).toBe(account.name);
        done();
      })
      .error(catchFail(done));

    $httpBackend.when('PUT', URLs.one, account).respond({
      account: account
    });
    $httpBackend.flush();
  });

});