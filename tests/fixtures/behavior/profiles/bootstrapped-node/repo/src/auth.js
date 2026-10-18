// Token check. Keep this small: auth changes are Lane A surface.
function isAuthorized(req) {
  return Boolean(req.headers && req.headers.authorization);
}

module.exports = { isAuthorized };
