(function (exports) {
  
  exports.catchFail = function (done) {
    return function (e) {
      console.error(e);
      done();
    }
  };
  
  exports.fail = function (error) {
    console.error(error);
    throw Error(error);
  };

  exports.checkObjectKeys = function(o, keys) {
    expect(_.keys(o).sort()).toEqual(keys.sort());
  };
  
})(global);