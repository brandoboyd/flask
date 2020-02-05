var _ = require('underscore')._;

module.exports.sendToSelf = function(socket, method, data) {
  socket.emit(method, data);
};

module.exports.sendToAllConnectedClients = function(io, method, data) {
  io.sockets.emit(method, data);
};

module.exports.sendToAllClientsInRoom = function(io, room, method, data) {
  io.sockets.in(room).emit(method, data);
};

module.exports.sendToUserByID = function(io, receiver, method, data, cb) {
    _.each(receiver.socketIDs, function(id) {
        io.sockets.socket(id).emit(method, data, cb);
    });
};

// Pad random-generated digits to the end of the string
function addSuffixNumber(str) {
    var random = Math.floor(Math.random()*1001);
    return str + random;
}

// Get the number of online customers by looping through the people collection
function getCustomerCount(people) {
    return _.filter(people, function(person) {
        return person.userType === 'customer';
    }).length;
}

// Check socketID exits in the people collection and returns the person object
function findPersonBySocket(people, socketID) {
    var index = -1;
    _.each(people, function(person, idx) {
        if (typeof _.findWhere(person.socketIDs, socketID) !== 'undefined') {
            index = idx;
        }
    });

    return (index !== -1)? people[index]: null;
}

// Find the person specified by the userID
function findPersonByID(people, userID) {
    var person = _.findWhere(people, {'userID': userID});
    return (person)? person: null;
}

// Insert a new element avoiding duplicates
function pushUnique(array, element) {
  if (typeof _.findWhere(array, element) === 'undefined') {
    array.push(element);
  }
}

// Check if the person has active sockets which represents he's online
function isOnline(person) {
    return !!person.socketIDs.length;
}

// From the given people and rooms, render open rooms and their agent & customer statistics
// Send back to the requester socket
function sendDiagnostics(io, people, rooms) {
    var superUser = _.findWhere(people, {userType: 'supervisor'});
    if (!superUser) return;

    var openRooms = [];

    _.each(rooms, function(room) {
        var owner = _.findWhere(people, {userID: room.owner});
        if (owner && isOnline(owner)) {
            var obj = {
                id          : room.id,
                name        : room.name,
                available   : room.available,
                owner       : {
                                id      : owner.userID,
                                name    : owner.userName,
                                socksNum: owner.socketIDs.length
                            },
                users       : _.map(room.users, function (e) {
                                return {
                                    id      : e.userID,
                                    name    : e.userName,
                                    socksNum: e.socketIDs.length
                                };
                            })
            };
            openRooms.push(obj);
        }
    });

    _.each(superUser.socketIDs, function(id) {
        io.sockets.socket(id).emit('sendDiagnostics', openRooms);
    });
}

exports.getCustomerCount = getCustomerCount;
exports.addSuffixNumber = addSuffixNumber;
exports.findPersonBySocket = findPersonBySocket;
exports.findPersonByID = findPersonByID;
exports.pushUnique = pushUnique;
exports.sendDiagnostics = sendDiagnostics;