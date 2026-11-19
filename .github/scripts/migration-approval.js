"use strict";

const APPROVAL_PATTERN = /^(approved|approve|lgtm|yes)[.!]?$/im;

/**
 * Return only repository collaborators who can modify repository contents.
 * GitHub exposes `push` for write access; `maintain` and `admin` are included
 * explicitly so this remains correct if GitHub changes the shape of `push`.
 */
function getAuthorizedApprovers(collaborators) {
  return collaborators
    .filter(({ login, permissions = {} }) =>
      Boolean(login) &&
      (permissions.push || permissions.maintain || permissions.admin),
    )
    .map(({ login }) => login)
    .sort((left, right) => left.localeCompare(right));
}

function hasAuthorizedApproval(comments, authorizedApprovers) {
  const authorized = new Set(authorizedApprovers);

  return comments.some(
    ({ body = "", user = {} }) =>
      authorized.has(user.login) && APPROVAL_PATTERN.test(body),
  );
}

module.exports = {
  getAuthorizedApprovers,
  hasAuthorizedApproval,
};
