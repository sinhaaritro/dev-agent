// HTTP entry point.
const { isAuthorized } = require("./auth");

function handle(req) {
  if (!isAuthorized(req)) {
    return { status: 401 };
  }
  return { status: 200, body: "ok" };
}

module.exports = { handle };
