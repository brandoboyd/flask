var utils = require('./utils');

function Room(name, id, owner) {
  this.name = name;
  this.id = id;
  this.owner = owner;
  this.users = [];
  this.available = true;
};

Room.prototype.addPerson = function(userID) {
  if (this.available) {
    utils.pushUnique(this.users, userID);
  }
};

Room.prototype.updateStatus = function(isAvailable) {
  this.available = isAvailable;
}

module.exports = Room;